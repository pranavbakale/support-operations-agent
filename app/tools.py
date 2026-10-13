from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.approvals import ApprovalStore
from app.repositories import AccountRepository, PolicyRepository, TicketRepository
from app.schemas import ProposedAction


class PolicySearchTool:
    name = "policy_search"
    mutates_records = False

    def __init__(self, repository: PolicyRepository, top_k: int) -> None:
        self.repository = repository
        self.top_k = top_k

    async def execute(self, query: str) -> list[dict[str, Any]]:
        hits = await self.repository.search(query=query, limit=self.top_k)
        return [
            {
                "policy_id": hit.policy_id,
                "slug": hit.slug,
                "title": hit.title,
                "body": hit.body,
                "score": hit.score,
            }
            for hit in hits
        ]


class AccountLookupTool:
    name = "account_lookup"
    mutates_records = False

    def __init__(self, repository: AccountRepository) -> None:
        self.repository = repository

    async def execute(self, account_id: str) -> dict[str, Any]:
        account = await self.repository.get(account_id)
        if account is None:
            raise LookupError(f"account {account_id} was not found")
        return {
            "id": account.id,
            "name": account.name,
            "plan": account.plan,
            "status": account.status,
            "created_at": account.created_at.isoformat(),
        }


class CreateTicketTool:
    name = "create_ticket"
    mutates_records = True

    def __init__(
        self,
        repository: TicketRepository,
        approvals: ApprovalStore,
        approval_ttl_seconds: int,
    ) -> None:
        self.repository = repository
        self.approvals = approvals
        self.approval_ttl_seconds = approval_ttl_seconds

    async def execute(
        self,
        *,
        account_id: str | None = None,
        subject: str | None = None,
        description: str | None = None,
        approval_id: str | None = None,
    ) -> ProposedAction | dict[str, Any]:
        if approval_id:
            action = await self.approvals.take(approval_id)
            if action is None:
                raise LookupError("approval was not found, expired, or already used")
            if action.tool != self.name:
                raise ValueError("approval does not match this tool")
            ticket = await self.repository.create(**action.arguments)
            return {"ticket_id": ticket.id, "status": ticket.status}

        if not account_id or not subject or not description:
            raise ValueError("account_id, subject, and description are required")

        action_id = str(uuid4())
        expires_at = datetime.now(UTC) + timedelta(seconds=self.approval_ttl_seconds)
        action = ProposedAction(
            id=action_id,
            tool="create_ticket",
            summary=f"Create a support ticket titled '{subject}'",
            arguments={
                "account_id": account_id,
                "subject": subject[:160],
                "description": description,
            },
            expires_at=expires_at,
        )
        await self.approvals.put(action, self.approval_ttl_seconds)
        return action


class ToolRegistry:
    def __init__(
        self,
        policy_search: PolicySearchTool,
        account_lookup: AccountLookupTool,
        create_ticket: CreateTicketTool,
    ) -> None:
        self._tools = {
            policy_search.name: policy_search,
            account_lookup.name: account_lookup,
            create_ticket.name: create_ticket,
        }

    @property
    def names(self) -> list[str]:
        return list(self._tools)

    def get(self, name: str) -> Any:
        return self._tools[name]
