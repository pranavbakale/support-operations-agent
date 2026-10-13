import re
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.schemas import Citation, ProposedAction, SupportResponse, ToolCall
from app.tools import ToolRegistry

CATEGORY_TERMS = {
    "billing": {"bill", "billing", "charge", "charged", "invoice", "payment", "refund"},
    "access": {"access", "locked", "login", "password", "signin", "2fa"},
    "subscription": {"cancel", "downgrade", "plan", "renewal", "subscription", "upgrade"},
    "privacy": {"data", "delete", "erase", "export", "privacy"},
}
ESCALATION_TERMS = {
    "agent",
    "escalate",
    "human",
    "representative",
    "someone",
    "ticket",
}
ROUTING_TERMS = ESCALATION_TERMS | {"create", "please", "support"}


@dataclass
class ToolExecution:
    output: Any
    record: ToolCall


def words(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def first_sentences(body: str, count: int = 2) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", body.strip())
    return " ".join(sentences[:count])


class SupportAgent:
    def __init__(self, tools: ToolRegistry) -> None:
        self.tools = tools

    async def _call(self, tool_name: str, **kwargs: Any) -> ToolExecution:
        started = perf_counter()
        try:
            output = await self.tools.get(tool_name).execute(**kwargs)
            record = ToolCall(
                tool=tool_name,
                success=True,
                latency_ms=round((perf_counter() - started) * 1000, 2),
            )
            return ToolExecution(output=output, record=record)
        except Exception as exc:
            record = ToolCall(
                tool=tool_name,
                success=False,
                latency_ms=round((perf_counter() - started) * 1000, 2),
                error=str(exc),
            )
            return ToolExecution(output=None, record=record)

    async def handle(self, account_id: str, message: str) -> SupportResponse:
        started = perf_counter()
        request_id = str(uuid4())
        calls: list[ToolCall] = []

        account_result = await self._call("account_lookup", account_id=account_id)
        calls.append(account_result.record)
        if not account_result.record.success:
            return SupportResponse(
                request_id=request_id,
                state="answered",
                message="I could not find that account. Check the account ID and try again.",
                citations=[],
                tool_calls=calls,
                latency_ms=round((perf_counter() - started) * 1000, 2),
            )

        policy_result = await self._call("policy_search", query=self._policy_query(message))
        calls.append(policy_result.record)
        raw_hits = policy_result.output or []
        citations = [
            Citation(
                marker=f"P{index}",
                policy_id=hit["policy_id"],
                slug=hit["slug"],
                title=hit["title"],
                excerpt=first_sentences(hit["body"], 1),
                score=hit["score"],
            )
            for index, hit in enumerate(raw_hits[:1], start=1)
        ]

        category = self._category(message)
        wants_escalation = bool(words(message) & ESCALATION_TERMS)
        should_propose_ticket = wants_escalation or not citations
        answer = self._grounded_answer(account_result.output, raw_hits, category)

        action: ProposedAction | None = None
        if should_propose_ticket:
            subject = f"{category.title()} support request" if category else "Support request"
            ticket_result = await self._call(
                "create_ticket",
                account_id=account_id,
                subject=subject,
                description=message,
            )
            calls.append(ticket_result.record)
            if ticket_result.record.success:
                action = ticket_result.output
                answer = (
                    f"{answer}\n\nI prepared a support ticket, but no record has been changed. "
                    "Approve the proposed action to create it."
                )

        return SupportResponse(
            request_id=request_id,
            state="awaiting_approval" if action else "answered",
            message=answer,
            citations=citations,
            tool_calls=calls,
            proposed_action=action,
            latency_ms=round((perf_counter() - started) * 1000, 2),
        )

    def _category(self, message: str) -> str | None:
        tokens = words(message)
        scored = [
            (len(tokens & terms), category) for category, terms in CATEGORY_TERMS.items()
        ]
        score, category = max(scored)
        return category if score else None

    def _policy_query(self, message: str) -> str:
        customer_terms = [
            token
            for token in re.findall(r"[a-z0-9]+", message.lower())
            if token not in ROUTING_TERMS
        ]
        return " ".join(customer_terms) or message

    def _grounded_answer(
        self, account: dict[str, Any], hits: list[dict[str, Any]], category: str | None
    ) -> str:
        name = account["name"].split()[0]
        if not hits:
            return (
                f"I do not have enough policy information to answer that safely, {name}. "
                "The next step is to send this to support."
            )

        fact = first_sentences(hits[0]["body"])
        context = f" For your {account['plan']} plan," if category == "subscription" else ""
        return f"{name},{context} {fact} [P1]"
