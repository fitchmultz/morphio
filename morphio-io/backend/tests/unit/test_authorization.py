from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.security.authorization import (
    Permission,
    check_permission,
    check_resource_owner,
    get_user_permissions,
)
from app.utils.error_handlers import ApplicationException


def _user(user_id: int = 1, *, is_admin: bool = False):
    return SimpleNamespace(id=user_id, is_admin=is_admin)


def _db_with_scalar(*values) -> tuple[AsyncSession, AsyncMock]:
    scalar = AsyncMock(side_effect=values)
    return cast(AsyncSession, SimpleNamespace(scalar=scalar)), scalar


@pytest.mark.asyncio
async def test_check_permission_rejects_non_admin_for_admin_permission():
    with pytest.raises(ApplicationException) as exc:
        await check_permission(Permission.ADMIN, _user())

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_check_resource_owner_allows_matching_content_owner():
    db, scalar = _db_with_scalar(7)

    assert await check_resource_owner(12, "content", _user(7), db)
    scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_resource_owner_rejects_mismatched_content_owner():
    db, _scalar = _db_with_scalar(8)

    with pytest.raises(ApplicationException) as exc:
        await check_resource_owner(12, "content", _user(7), db)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_check_resource_owner_allows_default_template():
    db, scalar = _db_with_scalar(None, True)

    assert await check_resource_owner(3, "template", _user(7), db)
    assert scalar.await_count == 2


@pytest.mark.asyncio
async def test_check_resource_owner_rejects_unknown_resource_type():
    db, scalar = _db_with_scalar()

    with pytest.raises(ApplicationException) as exc:
        await check_resource_owner(3, "unknown", _user(7), db)

    assert exc.value.status_code == 400
    scalar.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_user_permissions_uses_role_flags():
    assert await get_user_permissions(_user()) == [Permission.USER]
    assert await get_user_permissions(_user(is_admin=True)) == [
        Permission.USER,
        Permission.ADMIN,
    ]
