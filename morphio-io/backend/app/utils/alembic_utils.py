import os
from typing import Tuple

from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.config import Config


def _alembic_config_path() -> str:
    # Resolve alembic.ini relative to this file (backend/app/utils/ -> backend/alembic.ini)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base, "alembic.ini")


async def get_db_and_head_revision(async_engine) -> Tuple[str | None, str]:
    async with async_engine.begin() as conn:

        def _get_current(sync_conn):
            ctx = MigrationContext.configure(sync_conn)
            return ctx.get_current_revision()

        current = await conn.run_sync(_get_current)

    cfg = Config(_alembic_config_path())
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("No Alembic head revision found")
    return (current, head)


async def assert_alembic_up_to_date(async_engine, enforce: bool = False) -> Tuple[str | None, str]:
    """Return (current, head) and optionally raise if not up to date."""
    current, head = await get_db_and_head_revision(async_engine)
    if enforce and current != head:
        raise RuntimeError(
            f"Alembic revision mismatch: current={current} head={head}. Run 'alembic upgrade head'."
        )
    return current, head
