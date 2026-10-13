from datetime import UTC, datetime, timedelta

import pytest

from app.agent import SupportAgent
from app.schemas import ProposedAction
from app.tools import ToolRegistry


class FakeAccountLookup:
    name = "account_lookup"

    async def execute(self, account_id: str) -> dict:
        return {
            "id": account_id,
            "name": "Maya Chen",
            "plan": "pro",
            "status": "active",
            "created_at": "2026-01-01T00:00:00+00:00",
        }


class FakePolicySearch:
    name = "policy_search"

    async def execute(self, query: str) -> list[dict]:
        del query
        return [
            {
                "policy_id": "pol_refunds",
                "slug": "refunds-and-charges",
                "title": "Refunds and card charges",
                "body": "Refunds are eligible within 30 days. They return to the original card.",
                "score": 0.91,
            }
        ]


class FakeCreateTicket:
    name = "create_ticket"

    def __init__(self) -> None:
        self.execute_count = 0

    async def execute(self, **arguments) -> ProposedAction:
        self.execute_count += 1
        return ProposedAction(
            id="action-1",
            tool="create_ticket",
            summary="Create a support ticket",
            arguments=arguments,
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )


@pytest.fixture
def tool_registry() -> tuple[ToolRegistry, FakeCreateTicket]:
    ticket_tool = FakeCreateTicket()
    return (
        ToolRegistry(FakePolicySearch(), FakeAccountLookup(), ticket_tool),
        ticket_tool,
    )


async def test_grounded_answer_has_a_structured_citation(tool_registry) -> None:
    registry, ticket_tool = tool_registry

    response = await SupportAgent(registry).handle(
        "acct_1001", "Can I get a refund for a purchase from last week?"
    )

    assert response.state == "answered"
    assert response.citations[0].slug == "refunds-and-charges"
    assert "[P1]" in response.message
    assert ticket_tool.execute_count == 0
    assert [call.tool for call in response.tool_calls] == [
        "account_lookup",
        "policy_search",
    ]


async def test_escalation_proposes_ticket_without_claiming_it_was_created(tool_registry) -> None:
    registry, ticket_tool = tool_registry

    response = await SupportAgent(registry).handle(
        "acct_1001", "I was charged twice. Please create a ticket for a human agent."
    )

    assert response.state == "awaiting_approval"
    assert response.proposed_action is not None
    assert response.proposed_action.tool == "create_ticket"
    assert "no record has been changed" in response.message
    assert ticket_tool.execute_count == 1
