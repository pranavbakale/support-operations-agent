import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import SupportAgent
from app.approvals import ApprovalStore, RedisApprovalStore
from app.config import get_settings
from app.database import engine, get_session
from app.dependencies import build_tool_registry, get_approval_store
from app.repositories import AccountRepository, TicketRepository
from app.schemas import (
    AccountSummary,
    ApprovalResponse,
    HealthResponse,
    SupportRequest,
    SupportResponse,
    TicketResponse,
)

settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("support-api")
SessionDep = Annotated[AsyncSession, Depends(get_session)]
ApprovalDep = Annotated[ApprovalStore, Depends(get_approval_store)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis
    app.state.approvals = RedisApprovalStore(redis)
    yield
    await redis.aclose()
    await engine.dispose()


app = FastAPI(
    title="Support Operations Agent",
    version="1.0.0",
    description="Policy-grounded support workflows with approval-gated record changes.",
    lifespan=lifespan,
)
project_root = Path(__file__).resolve().parent.parent
static_root = project_root / "app" / "static"
app.mount("/static", StaticFiles(directory=static_root), name="static")


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s latency_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        (perf_counter() - started) * 1000,
    )
    return response


@app.get("/", include_in_schema=False)
async def application_shell() -> FileResponse:
    return FileResponse(static_root / "index.html")


@app.get("/styles.css", include_in_schema=False)
async def application_styles() -> FileResponse:
    return FileResponse(static_root / "styles.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
async def application_script() -> FileResponse:
    return FileResponse(static_root / "app.js", media_type="text/javascript")


@app.get("/health", response_model=HealthResponse)
async def health(
    session: SessionDep,
    approvals: ApprovalDep,
) -> HealthResponse:
    postgres_ok = redis_ok = False
    try:
        postgres_ok = bool(await session.scalar(text("SELECT 1")))
    except Exception:
        logger.exception("postgres health check failed")
    try:
        redis_ok = await approvals.ping()
    except Exception:
        logger.exception("redis health check failed")
    return HealthResponse(
        status="ok" if postgres_ok and redis_ok else "degraded",
        postgres=postgres_ok,
        redis=redis_ok,
    )


@app.get("/v1/tools")
async def list_tools(
    session: SessionDep,
    approvals: ApprovalDep,
) -> dict[str, list[str]]:
    return {"tools": build_tool_registry(session, approvals).names}


@app.get("/v1/accounts", response_model=list[AccountSummary])
async def list_accounts(session: SessionDep) -> list[AccountSummary]:
    accounts = await AccountRepository(session).list()
    return [AccountSummary.model_validate(account, from_attributes=True) for account in accounts]


@app.get("/v1/benchmark")
async def benchmark_summary() -> dict:
    return json.loads((project_root / "eval" / "baseline.json").read_text(encoding="utf-8"))


@app.post("/v1/support/messages", response_model=SupportResponse)
async def support_message(
    payload: SupportRequest,
    session: SessionDep,
    approvals: ApprovalDep,
) -> SupportResponse:
    agent = SupportAgent(build_tool_registry(session, approvals))
    return await agent.handle(payload.account_id, payload.message)


@app.post("/v1/approvals/{action_id}/approve", response_model=ApprovalResponse)
async def approve_action(
    action_id: str,
    session: SessionDep,
    approvals: ApprovalDep,
) -> ApprovalResponse:
    tool = build_tool_registry(session, approvals).get("create_ticket")
    try:
        result = await tool.execute(approval_id=action_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApprovalResponse(action_id=action_id, status="approved", ticket_id=result["ticket_id"])


@app.post("/v1/approvals/{action_id}/reject", response_model=ApprovalResponse)
async def reject_action(
    action_id: str,
    approvals: ApprovalDep,
) -> ApprovalResponse:
    if not await approvals.delete(action_id):
        raise HTTPException(status_code=404, detail="approval was not found or expired")
    return ApprovalResponse(action_id=action_id, status="rejected")


@app.get("/v1/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str, session: SessionDep
) -> TicketResponse:
    ticket = await TicketRepository(session).get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    return TicketResponse.model_validate(ticket, from_attributes=True)


@app.get("/v1/tickets", response_model=list[TicketResponse])
async def list_tickets(account_id: str, session: SessionDep) -> list[TicketResponse]:
    tickets = await TicketRepository(session).list_for_account(account_id)
    return [TicketResponse.model_validate(ticket, from_attributes=True) for ticket in tickets]
