"""Purpose: Resolve content tag names into persisted tag models.
Responsibilities: Normalize user-supplied tag names and attach/create Tag records safely.
Scope: Content create/update flows that accept string tag lists from API callers.
Usage: Imported by content CRUD routes before persisting Content ORM models.
Invariants/Assumptions: Returned tags are deduplicated, trimmed, and suitable for SQLAlchemy relationship assignment.
"""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.tag import Tag


async def resolve_content_tags(
    session: AsyncSession,
    tag_names: Iterable[str] | None,
) -> list[Tag]:
    """Normalize and load/create tag models for a content payload."""
    if not tag_names:
        return []

    normalized_names: list[str] = []
    seen_names: set[str] = set()
    for raw_name in tag_names:
        name = raw_name.strip()
        if not name:
            continue
        dedupe_key = name.lower()
        if dedupe_key in seen_names:
            continue
        seen_names.add(dedupe_key)
        normalized_names.append(name)

    if not normalized_names:
        return []

    existing = await session.execute(select(Tag).where(Tag.name.in_(normalized_names)))
    tags_by_name = {tag.name: tag for tag in existing.scalars().all()}

    resolved_tags: list[Tag] = []
    for name in normalized_names:
        tag = tags_by_name.get(name)
        if tag is None:
            tag = Tag(name=name)
            session.add(tag)
            await session.flush()
            tags_by_name[name] = tag
        resolved_tags.append(tag)

    return resolved_tags
