"""Fix contents.template_id type to Integer.

Revision ID: 20251231_fix_template_id_type
Revises: 20251223_add_billing_and_api_keys
Create Date: 2025-12-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251231_fix_template_id_type"
down_revision: str | None = "20251223_add_billing_and_api_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    with op.batch_alter_table("contents") as batch:
        if dialect == "postgresql":
            batch.alter_column(
                "template_id",
                type_=sa.Integer(),
                postgresql_using="template_id::integer",
            )
        else:
            batch.alter_column("template_id", type_=sa.Integer())
        batch.create_foreign_key(
            "fk_contents_template_id_templates",
            "templates",
            ["template_id"],
            ["id"],
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    with op.batch_alter_table("contents") as batch:
        batch.drop_constraint("fk_contents_template_id_templates", type_="foreignkey")
        if dialect == "postgresql":
            batch.alter_column(
                "template_id",
                type_=sa.Text(),
                postgresql_using="template_id::text",
            )
        else:
            batch.alter_column("template_id", type_=sa.Text())
