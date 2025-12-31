"""Add indexes for usage queries.

Revision ID: 20251231_add_usage_indexes
Revises: 20251231_fix_template_id_type
Create Date: 2025-12-31
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251231_add_usage_indexes"
down_revision: str | None = "20251231_fix_template_id_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_usages_user_id", "usages", ["user_id"], unique=False)
    op.create_index(
        "ix_usages_user_id_created_at",
        "usages",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_usages_user_id_created_at", table_name="usages")
    op.drop_index("ix_usages_user_id", table_name="usages")
