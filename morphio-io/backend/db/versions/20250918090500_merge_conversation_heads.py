"""merge heads after content conversations and template updates

Revision ID: 20250918090500
Revises: 20250918090000, 5c41813cd26c
Create Date: 2025-09-18 09:05:00.000000
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250918090500"
down_revision: tuple[str, str] = ("20250918090000", "5c41813cd26c")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op merge migration."""
    pass


def downgrade() -> None:
    """No-op merge migration."""
    pass
