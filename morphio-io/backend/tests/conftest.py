import os
import warnings
from typing import AsyncGenerator
from unittest.mock import patch  # Ensure 'patch' is imported

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

os.environ["APP_ENV"] = "development"  # Ensure relaxed settings during tests
os.environ["JWT_SECRET_KEY"] = "test_secret_key"  # Set before imports
os.environ["RATE_LIMITING_ENABLED"] = "False"  # Disable rate limiting for tests

from app.database import get_db
from app.main import app

# Import all models to ensure they are registered with Base.metadata before create_all
from app.models import (
    APIKey,
    Base,
    Comment,
    Content,
    ContentConversation,
    ConversationMessage,
    LLMUsageRecord,
    Subscription,
    Tag,
    Template,
    Usage,
    User,
)

# Ensure models are registered
_ = [
    APIKey,
    Comment,
    Content,
    ContentConversation,
    ConversationMessage,
    LLMUsageRecord,
    Subscription,
    Tag,
    Template,
    Usage,
    User,
]

TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

warnings.filterwarnings("ignore", category=DeprecationWarning, module="jose.jwt")


@pytest.fixture(scope="function")
async def prepare_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def db_session(prepare_database) -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(client: AsyncClient) -> AsyncClient:
    return client


def pytest_configure(config):
    warnings.simplefilter("always", DeprecationWarning)
    warnings.simplefilter("always", PendingDeprecationWarning)


@pytest.fixture
def mock_rate_limit():
    with patch("app.utils.decorators.rate_limit") as mock:
        mock.side_effect = (
            lambda limit: lambda f: f
        )  # Disable rate limiting for tests except specific ones
        yield mock


def pytest_sessionfinish(session, exitstatus):
    """Cleanup resources after all tests complete to prevent hanging."""
    import asyncio

    # Close Redis connections (synchronous)
    try:
        from app.utils import decorators

        if hasattr(decorators, "redis_client"):
            decorators.redis_client.close()
    except Exception:
        pass

    async def cleanup():
        # Dispose test engine
        await engine.dispose()
        # Dispose app engine (imported from app.main -> app.database)
        from app.database import engine as app_engine

        await app_engine.dispose()

    # Run cleanup without deprecated implicit event-loop access.
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(cleanup())
    else:
        loop.create_task(cleanup())
