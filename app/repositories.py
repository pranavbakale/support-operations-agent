import re
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, PolicyArticle, Ticket

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "for",
    "how",
    "i",
    "is",
    "it",
    "me",
    "my",
    "of",
    "please",
    "the",
    "to",
    "what",
    "was",
    "why",
    "you",
}

SYNONYMS = {
    "signin": {"login", "password", "access"},
    "login": {"password", "access", "locked"},
    "charged": {"billing", "charge", "payment", "refund"},
    "charge": {"billing", "payment", "refund"},
    "cancel": {"subscription", "cancellation"},
    "erase": {"delete", "privacy", "data"},
    "human": {"support", "ticket", "agent"},
}


@dataclass(frozen=True)
class PolicyHit:
    policy_id: str
    slug: str
    title: str
    body: str
    score: float


def query_terms(query: str) -> set[str]:
    terms = {
        token
        for token in re.findall(r"[a-z0-9]+", query.lower())
        if len(token) > 1 and token not in STOP_WORDS
    }
    for term in tuple(terms):
        terms.update(SYNONYMS.get(term, set()))
    return terms


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, account_id: str) -> Account | None:
        return await self.session.get(Account, account_id)

    async def list(self) -> list[Account]:
        statement = select(Account).order_by(Account.name.asc())
        return list((await self.session.scalars(statement)).all())


class PolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, query: str, limit: int) -> list[PolicyHit]:
        terms = query_terms(query)
        if not terms:
            return []

        bind = self.session.get_bind()
        if bind.dialect.name == "postgresql":
            hits = await self._postgres_search(terms, limit)
            if hits:
                return hits

        rows = (await self.session.scalars(select(PolicyArticle))).all()
        ranked: list[PolicyHit] = []
        for article in rows:
            title_terms = query_terms(article.title)
            body_terms = query_terms(f"{article.body} {article.tags}")
            overlap = terms & (title_terms | body_terms)
            if not overlap:
                continue
            score = (2 * len(overlap & title_terms) + len(overlap & body_terms)) / len(terms)
            ranked.append(
                PolicyHit(
                    policy_id=article.id,
                    slug=article.slug,
                    title=article.title,
                    body=article.body,
                    score=round(score, 4),
                )
            )
        return sorted(ranked, key=lambda item: (-item.score, item.slug))[:limit]

    async def _postgres_search(self, terms: set[str], limit: int) -> list[PolicyHit]:
        tsquery = " | ".join(sorted(terms))
        statement = text(
            """
            SELECT id, slug, title, body,
                   ts_rank_cd(
                       to_tsvector('english', title || ' ' || body || ' ' || tags),
                       to_tsquery('english', :query)
                   ) AS score
            FROM policy_articles
            WHERE to_tsvector('english', title || ' ' || body || ' ' || tags)
                  @@ to_tsquery('english', :query)
            ORDER BY score DESC, slug ASC
            LIMIT :limit
            """
        )
        rows = (await self.session.execute(statement, {"query": tsquery, "limit": limit})).all()
        return [
            PolicyHit(
                policy_id=row.id,
                slug=row.slug,
                title=row.title,
                body=row.body,
                score=round(float(row.score), 4),
            )
            for row in rows
        ]


class TicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, account_id: str, subject: str, description: str) -> Ticket:
        ticket = Ticket(account_id=account_id, subject=subject, description=description)
        self.session.add(ticket)
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket

    async def get(self, ticket_id: str) -> Ticket | None:
        return await self.session.get(Ticket, ticket_id)

    async def list_for_account(self, account_id: str, limit: int = 10) -> list[Ticket]:
        statement = (
            select(Ticket)
            .where(Ticket.account_id == account_id)
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(statement)).all())
