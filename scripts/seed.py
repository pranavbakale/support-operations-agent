import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.database import SessionFactory, engine
from app.models import Account, PolicyArticle

ACCOUNTS = [
    {
        "id": "acct_1001",
        "email": "maya.chen@example.test",
        "name": "Maya Chen",
        "plan": "pro",
        "status": "active",
    },
    {
        "id": "acct_1002",
        "email": "jon.bell@example.test",
        "name": "Jon Bell",
        "plan": "starter",
        "status": "active",
    },
    {
        "id": "acct_1003",
        "email": "amina.yusuf@example.test",
        "name": "Amina Yusuf",
        "plan": "business",
        "status": "past_due",
    },
]

POLICIES = [
    {
        "id": "pol_refunds",
        "slug": "refunds-and-charges",
        "title": "Refunds and card charges",
        "tags": "billing payment charged duplicate unauthorized refund invoice",
        "body": (
            "Refund requests are eligible within 30 days of the original purchase. "
            "Approved refunds return to the original payment method in five to ten business "
            "days. Duplicate or unrecognized charges should be reported immediately so the "
            "billing team can investigate."
        ),
    },
    {
        "id": "pol_passwords",
        "slug": "password-and-account-access",
        "title": "Password reset and account access",
        "tags": "login signin password locked access 2fa reset",
        "body": (
            "Password reset links expire after 30 minutes and can only be used once. "
            "Five failed sign-in attempts lock the account for 15 minutes. Support can send "
            "a new reset link but cannot view or set a customer's password."
        ),
    },
    {
        "id": "pol_subscriptions",
        "slug": "subscription-changes",
        "title": "Subscription upgrades, downgrades, and cancellations",
        "tags": "plan subscription upgrade downgrade cancel cancellation renewal prorated",
        "body": (
            "Plan upgrades take effect immediately and receive a prorated charge. "
            "Downgrades start on the next renewal date. A canceled subscription remains active "
            "through the end of its current paid billing period."
        ),
    },
    {
        "id": "pol_privacy",
        "slug": "privacy-and-data-requests",
        "title": "Privacy, data export, and deletion requests",
        "tags": "privacy data export delete deletion erase retention",
        "body": (
            "Account data exports are normally ready within 48 hours. Deletion requests require "
            "identity verification and are completed within 30 days. Billing records may be "
            "retained where required for tax and fraud prevention."
        ),
    },
    {
        "id": "pol_incidents",
        "slug": "service-incidents",
        "title": "Service incidents and troubleshooting",
        "tags": "outage error broken unavailable troubleshooting incident status",
        "body": (
            "Check the status page before opening an incident ticket. Include the request ID, "
            "timestamp, and steps to reproduce when a problem continues. Critical incidents are "
            "reserved for production outages or security events."
        ),
    },
    {
        "id": "pol_ticketing",
        "slug": "ticket-priority-and-response-times",
        "title": "Ticket priority and response times",
        "tags": "ticket support human agent priority response escalate representative",
        "body": (
            "Support tickets are prioritized by customer impact rather than submission order. "
            "Business-plan production incidents have a two-hour response target; standard "
            "requests have a one-business-day response target."
        ),
    },
]


async def seed() -> None:
    async with SessionFactory() as session:
        for payload in ACCOUNTS:
            existing = await session.get(Account, payload["id"])
            if existing is None:
                session.add(Account(**payload, created_at=datetime.now(UTC)))

        for payload in POLICIES:
            existing = await session.scalar(
                select(PolicyArticle).where(PolicyArticle.slug == payload["slug"])
            )
            if existing is None:
                session.add(PolicyArticle(**payload, updated_at=datetime.now(UTC)))
            else:
                existing.title = payload["title"]
                existing.body = payload["body"]
                existing.tags = payload["tags"]
                existing.updated_at = datetime.now(UTC)
        await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
