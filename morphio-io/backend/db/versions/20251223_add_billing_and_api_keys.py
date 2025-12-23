"""Add Stripe billing fields and API keys table.

Revision ID: 20251223_add_billing_and_api_keys
Revises: 20251223_add_llm_usage_records
Create Date: 2025-12-23

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251223_add_billing_and_api_keys"
down_revision = "20251223_add_llm_usage_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Stripe billing fields to users table
    op.add_column(
        "users",
        sa.Column("stripe_customer_id", sa.String(255), nullable=True, index=True),
    )
    op.add_column(
        "users",
        sa.Column("subscription_status", sa.String(50), nullable=True),
    )

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("hashed_key", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "stripe_customer_id")
