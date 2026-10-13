from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals import ApprovalStore
from app.config import get_settings
from app.repositories import AccountRepository, PolicyRepository, TicketRepository
from app.tools import AccountLookupTool, CreateTicketTool, PolicySearchTool, ToolRegistry


def build_tool_registry(session: AsyncSession, approvals: ApprovalStore) -> ToolRegistry:
    settings = get_settings()
    return ToolRegistry(
        policy_search=PolicySearchTool(PolicyRepository(session), settings.policy_top_k),
        account_lookup=AccountLookupTool(AccountRepository(session)),
        create_ticket=CreateTicketTool(
            TicketRepository(session), approvals, settings.approval_ttl_seconds
        ),
    )


def get_approval_store(request: Request) -> ApprovalStore:
    return request.app.state.approvals
