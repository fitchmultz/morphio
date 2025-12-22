"""Re-introduce usage table with usage_type and usage_credits

Revision ID: aaaa_add_usage_type_credits
Revises: 20250213120000
Create Date: 2025-02-13 19:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "aaaa_add_usage_type_credits"
down_revision = "20250213120000"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("usage_type", sa.String(), nullable=False, server_default="other"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Unique index on (user_id, usage_type) so each user/usage_type pair is unique
    op.create_index(
        "ix_usages_user_id_usage_type", "usages", ["user_id", "usage_type"], unique=True
    )


def downgrade():
    op.drop_index("ix_usages_user_id_usage_type", table_name="usages")
    op.drop_table("usages")
