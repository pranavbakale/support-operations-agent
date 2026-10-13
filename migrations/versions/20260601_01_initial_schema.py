"""Create support operations tables.

Revision ID: 20260601_01
Revises:
Create Date: 2026-06-01
"""

import sqlalchemy as sa
from alembic import op

revision = "20260601_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("plan", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounts_email", "accounts", ["email"], unique=True)

    op.create_table(
        "policy_articles",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags", sa.String(length=300), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policy_articles_slug", "policy_articles", ["slug"], unique=True)
    op.execute(
        """
        CREATE INDEX ix_policy_articles_search
        ON policy_articles USING GIN (
            to_tsvector('english', title || ' ' || body || ' ' || tags)
        )
        """
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tickets_account_id", "tickets", ["account_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tickets_account_id", table_name="tickets")
    op.drop_table("tickets")
    op.drop_index("ix_policy_articles_search", table_name="policy_articles")
    op.drop_index("ix_policy_articles_slug", table_name="policy_articles")
    op.drop_table("policy_articles")
    op.drop_index("ix_accounts_email", table_name="accounts")
    op.drop_table("accounts")
