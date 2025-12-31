import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.user import User
from app.services.security import get_current_user
from app.utils import json_cache

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_templates_list_uses_cache(client, monkeypatch):
    store: dict[str, str] = {}

    async def fake_get(key: str):
        return store.get(key)

    async def fake_set(key: str, value, expire: int = 3600):
        store[key] = json.dumps(value)
        return True

    monkeypatch.setattr(json_cache, "get_redis_data", fake_get)
    monkeypatch.setattr(json_cache, "set_redis_data", fake_set)
    monkeypatch.setattr(json_cache, "is_redis_available", lambda: True)
    monkeypatch.setattr(settings, "CACHE_TEMPLATES_ENABLED", True)
    monkeypatch.setattr(settings, "CACHE_TEMPLATES_TTL_S", 300)

    user = User(
        id=1,
        email="tester@example.com",
        hashed_password="hashed-password",
        display_name="Test User",
    )

    async def override_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_current_user

    template_payload = [
        {
            "id": 1,
            "name": "Default Template",
            "template_content": "Summary: {transcript}",
            "is_default": True,
            "user_id": None,
            "created_at": datetime.now(UTC),
        }
    ]

    try:
        with patch(
            "app.routes.template.get_all_templates",
            AsyncMock(return_value=template_payload),
        ) as mock_get_all:
            response_1 = await client.get("/template/get-templates")
            response_2 = await client.get("/template/get-templates")

        assert response_1.status_code == 200
        assert response_2.status_code == 200
        assert mock_get_all.call_count == 1
        assert len(response_2.json()["data"]) == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
