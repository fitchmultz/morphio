"""Add LLM usage records table for detailed token tracking.

Revision ID: 20251223_llm_usage
Revises: 20250918090500
Create Date: 2025-12-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251223_llm_usage"
down_revision: str | None = "20250918090500"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("contents.id"), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("model_alias", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), default=0),
        sa.Column("output_tokens", sa.Integer(), default=0),
        sa.Column("total_tokens", sa.Integer(), default=0),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("operation", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for common queries
    op.create_index("ix_llm_usage_records_user_id", "llm_usage_records", ["user_id"])
    op.create_index("ix_llm_usage_records_content_id", "llm_usage_records", ["content_id"])
    op.create_index("ix_llm_usage_records_created_at", "llm_usage_records", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_records_created_at", table_name="llm_usage_records")
    op.drop_index("ix_llm_usage_records_content_id", table_name="llm_usage_records")
    op.drop_index("ix_llm_usage_records_user_id", table_name="llm_usage_records")
    op.drop_table("llm_usage_records")
