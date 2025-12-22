"""add content conversations and messages tables

Revision ID: 20250918090000
Revises: 20250213120000
Create Date: 2025-09-18 09:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250918090000"
down_revision: Union[str, None] = "20250213120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("template_used", sa.String(length=255), nullable=True),
        sa.Column("original_transcript", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("context_snapshot", sa.JSON(), nullable=True),
        sa.Column("parent_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["contents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint([
            "user_id"
        ], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint([
            "template_id"
        ], ["templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint([
            "parent_id"
        ], ["content_conversations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_conversations_id", "content_conversations", ["id"], unique=False)
    op.create_index(
        "ix_content_conversations_content_id",
        "content_conversations",
        ["content_id"],
        unique=False,
    )
    op.create_index(
        "ix_content_conversations_user_id", "content_conversations", ["user_id"], unique=False
    )

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["content_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_messages_id", "conversation_messages", ["id"], unique=False)
    op.create_index(
        "ix_conversation_messages_conversation_id",
        "conversation_messages",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_messages_conversation_id", table_name="conversation_messages")
    op.drop_index("ix_conversation_messages_id", table_name="conversation_messages")
    op.drop_table("conversation_messages")

    op.drop_index("ix_content_conversations_user_id", table_name="content_conversations")
    op.drop_index("ix_content_conversations_content_id", table_name="content_conversations")
    op.drop_index("ix_content_conversations_id", table_name="content_conversations")
    op.drop_table("content_conversations")
