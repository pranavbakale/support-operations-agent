from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SupportRequest(BaseModel):
    account_id: str = Field(min_length=3, max_length=32)
    message: str = Field(min_length=3, max_length=2000)


class Citation(BaseModel):
    marker: str
    policy_id: str
    slug: str
    title: str
    excerpt: str
    score: float


class ToolCall(BaseModel):
    tool: str
    success: bool
    latency_ms: float
    error: str | None = None


class ProposedAction(BaseModel):
    id: str
    tool: Literal["create_ticket"]
    summary: str
    arguments: dict[str, Any]
    expires_at: datetime


class SupportResponse(BaseModel):
    request_id: str
    state: Literal["answered", "awaiting_approval"]
    message: str
    citations: list[Citation]
    tool_calls: list[ToolCall]
    proposed_action: ProposedAction | None = None
    latency_ms: float
    estimated_cost_usd: float = 0.0


class ApprovalResponse(BaseModel):
    action_id: str
    status: Literal["approved", "rejected"]
    ticket_id: str | None = None


class TicketResponse(BaseModel):
    id: str
    account_id: str
    subject: str
    description: str
    status: str
    created_at: datetime


class AccountSummary(BaseModel):
    id: str
    name: str
    plan: str
    status: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    postgres: bool
    redis: bool
