from types import SimpleNamespace

import pytest

from app.approvals import InMemoryApprovalStore
from app.tools import CreateTicketTool


class FakeTicketRepository:
    def __init__(self) -> None:
        self.created: list[dict] = []

    async def create(self, **arguments):
        self.created.append(arguments)
        return SimpleNamespace(id="ticket-1", status="open")


async def test_ticket_is_written_only_after_a_single_use_approval() -> None:
    repository = FakeTicketRepository()
    approvals = InMemoryApprovalStore()
    tool = CreateTicketTool(repository, approvals, approval_ttl_seconds=900)

    proposal = await tool.execute(
        account_id="acct_1001",
        subject="Billing support request",
        description="I was charged twice.",
    )

    assert repository.created == []
    assert await approvals.get(proposal.id) == proposal

    result = await tool.execute(approval_id=proposal.id)

    assert result == {"ticket_id": "ticket-1", "status": "open"}
    assert len(repository.created) == 1

    with pytest.raises(LookupError, match="expired, or already used"):
        await tool.execute(approval_id=proposal.id)


async def test_rejected_approval_cannot_be_used() -> None:
    repository = FakeTicketRepository()
    approvals = InMemoryApprovalStore()
    tool = CreateTicketTool(repository, approvals, approval_ttl_seconds=900)
    proposal = await tool.execute(
        account_id="acct_1001",
        subject="Access support request",
        description="I cannot sign in.",
    )

    assert await approvals.delete(proposal.id)
    with pytest.raises(LookupError):
        await tool.execute(approval_id=proposal.id)
    assert repository.created == []
