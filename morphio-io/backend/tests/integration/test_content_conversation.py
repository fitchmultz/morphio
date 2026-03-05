import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.content import Content
from app.models.conversation import ContentConversation, ConversationMessage
from app.models.user import User
from app.services.security import get_current_user
from app.utils.enums import ResponseStatus

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture
async def conversation_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(conversation_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=conversation_engine, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_continue_conversation_creates_new_thread(client, db_session):
    user = User(
        email="tester@example.com",
        display_name="Test User",
        hashed_password="hashed-password",
    )
    db_session.add(user)
    await db_session.flush()

    content = Content(
        title="Initial Draft",
        content="This is the original content body that needs refinement.",
        user_id=user.id,
        is_published=False,
    )
    db_session.add(content)
    await db_session.commit()

    async def override_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_current_user

    llm_payload = json.dumps(
        {
            "updated_content": "# Final Output\n\nRefined content tailored to the request.",
            "change_summary": ["Shortened introduction"],
            "notes": "Applied request for brevity.",
        }
    )

    try:
        with patch(
            "app.services.conversation.manager.generate_conversation_completion",
            new=AsyncMock(return_value=(llm_payload, "gpt-5.1")),
        ):
            response = await client.post(
                f"/content/{content.id}/conversation",
                json={"message": "Please make this more concise"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == ResponseStatus.SUCCESS
        data = body["data"]
        assert data["updated_content"].startswith("# Final Output")
        assert data["model_used"] == "gpt-5.1"
        assert data["change_summary"] == ["Shortened introduction"]
        assert len(data["messages"]) == 2  # user + assistant messages
        assert data["conversation_id"]
        conversation_id = data["conversation_id"]

        # Content should be updated in the database
        refreshed_content = await db_session.get(Content, content.id)
        assert refreshed_content is not None
        assert refreshed_content.content.startswith("# Final Output")

        # Conversation persisted with messages
        conversation_result = await db_session.execute(
            select(ContentConversation).where(ContentConversation.id == conversation_id)
        )
        conversation = conversation_result.scalar_one()
        assert conversation.model == "gpt-5.1"
        messages_result = await db_session.execute(
            select(ConversationMessage).where(
                ConversationMessage.conversation_id == conversation_id
            )
        )
        messages = messages_result.scalars().all()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

        # Fetch conversation summaries
        summary_response = await client.get(f"/content/{content.id}/conversations")
        assert summary_response.status_code == 200
        summary_body = summary_response.json()
        assert summary_body["status"] == ResponseStatus.SUCCESS
        assert len(summary_body["data"]) == 1
        assert summary_body["data"][0]["message_count"] == 2

        # Fetch full conversation thread
        thread_response = await client.get(f"/content/{content.id}/conversations/{conversation_id}")
        assert thread_response.status_code == 200
        thread_body = thread_response.json()
        assert thread_body["status"] == ResponseStatus.SUCCESS
        thread_data = thread_body["data"]
        assert thread_data["id"] == conversation_id
        assert len(thread_data["messages"]) == 2
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_continue_conversation_preserves_context(client, db_session):
    user = User(
        email="tester2@example.com",
        display_name="Test User 2",
        hashed_password="hashed-password",
    )
    db_session.add(user)
    await db_session.flush()

    content = Content(
        title="Test Content",
        content="Original content.",
        user_id=user.id,
        is_published=False,
    )
    db_session.add(content)
    await db_session.commit()

    async def override_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_current_user

    llm_payload_1 = json.dumps(
        {
            "updated_content": "# First Edit\n\nUpdated content.",
            "change_summary": ["Added heading"],
            "notes": None,
        }
    )

    llm_payload_2 = json.dumps(
        {
            "updated_content": "# First Edit\n\nUpdated content with more details.",
            "change_summary": ["Added more detail"],
            "notes": None,
        }
    )

    try:
        with patch(
            "app.services.conversation.manager.generate_conversation_completion",
            AsyncMock(side_effect=[(llm_payload_1, "gpt-5.1"), (llm_payload_2, "gpt-5.1")]),
        ):
            # First message
            response1 = await client.post(
                f"/content/{content.id}/conversation",
                json={"message": "Add a heading"},
            )
            assert response1.status_code == 200
            data1 = response1.json()["data"]
            conversation_id = data1["conversation_id"]

            # Second message in same conversation
            response2 = await client.post(
                f"/content/{content.id}/conversation",
                json={
                    "message": "Add more detail",
                    "conversation_id": conversation_id,
                    "preserve_context": True,
                },
            )
            assert response2.status_code == 200
            data2 = response2.json()["data"]
            assert data2["conversation_id"] == conversation_id
            assert len(data2["messages"]) == 4  # 2 user + 2 assistant

            # Verify conversation persisted
            conversation_result = await db_session.execute(
                select(ContentConversation).where(ContentConversation.id == conversation_id)
            )
            conversation = conversation_result.scalar_one()
            assert conversation.model == "gpt-5.1"
            assert len(conversation.messages) == 4
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_conversation_not_found_returns_404(client, db_session):
    user = User(
        email="tester3@example.com",
        display_name="Test User 3",
        hashed_password="hashed-password",
    )
    db_session.add(user)
    await db_session.flush()

    content = Content(
        title="Test Content",
        content="Original content.",
        user_id=user.id,
        is_published=False,
    )
    db_session.add(content)
    await db_session.commit()

    async def override_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = await client.post(
            f"/content/{content.id}/conversation",
            json={
                "message": "Test message",
                "conversation_id": "nonexistent-id-12345",
                "preserve_context": True,
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["message"].lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_conversation_message_length_validation(client, db_session):
    user = User(
        email="tester4@example.com",
        display_name="Test User 4",
        hashed_password="hashed-password",
    )
    db_session.add(user)
    await db_session.flush()

    content = Content(
        title="Test Content",
        content="Original content.",
        user_id=user.id,
        is_published=False,
    )
    db_session.add(content)
    await db_session.commit()

    async def override_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_current_user

    try:
        # Message too long (over 5000 characters)
        long_message = "x" * 5001
        response = await client.post(
            f"/content/{content.id}/conversation",
            json={"message": long_message},
        )
        assert (
            response.status_code == 400
        )  # Validation error (FastAPI returns 400 for validation errors)
        assert (
            "too long" in response.json()["message"].lower() or "5000" in response.json()["message"]
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_fetch_conversations_filters_soft_deleted(client, db_session):
    user = User(
        email="tester5@example.com",
        display_name="Test User 5",
        hashed_password="hashed-password",
    )
    db_session.add(user)
    await db_session.flush()

    content = Content(
        title="Test Content",
        content="Original content.",
        user_id=user.id,
        is_published=False,
    )
    db_session.add(content)
    await db_session.commit()

    async def override_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_current_user

    llm_payload = json.dumps(
        {
            "updated_content": "# Updated\n\nContent.",
            "change_summary": ["Updated"],
            "notes": None,
        }
    )

    try:
        with patch(
            "app.services.conversation.manager.generate_conversation_completion",
            AsyncMock(return_value=(llm_payload, "gpt-5.1")),
        ):
            # Create a conversation
            response = await client.post(
                f"/content/{content.id}/conversation",
                json={"message": "Update this"},
            )
            assert response.status_code == 200
            data = response.json()["data"]
            conversation_id = data["conversation_id"]

            # Soft delete the conversation
            from app.models.conversation import ContentConversation
            from datetime import datetime, UTC

            conversation_result = await db_session.execute(
                select(ContentConversation).where(ContentConversation.id == conversation_id)
            )
            conversation = conversation_result.scalar_one()
            conversation.deleted_at = datetime.now(UTC)
            await db_session.commit()

            # Verify it's not in the list
            list_response = await client.get(f"/content/{content.id}/conversations")
            assert list_response.status_code == 200
            conversations = list_response.json()["data"]
            assert len(conversations) == 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_conversation_branching(client, db_session):
    user = User(
        email="tester6@example.com",
        display_name="Test User 6",
        hashed_password="hashed-password",
    )
    db_session.add(user)
    await db_session.flush()

    content = Content(
        title="Test Content",
        content="Original content.",
        user_id=user.id,
        is_published=False,
    )
    db_session.add(content)
    await db_session.commit()

    async def override_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_current_user

    llm_payload_1 = json.dumps(
        {
            "updated_content": "# Branch 1\n\nContent version 1.",
            "change_summary": ["Version 1"],
            "notes": None,
        }
    )

    llm_payload_2 = json.dumps(
        {
            "updated_content": "# Branch 2\n\nContent version 2.",
            "change_summary": ["Version 2"],
            "notes": None,
        }
    )

    try:
        with patch(
            "app.services.conversation.manager.generate_conversation_completion",
            AsyncMock(side_effect=[(llm_payload_1, "gpt-5.1"), (llm_payload_2, "gpt-5.1")]),
        ):
            # Create initial conversation
            response1 = await client.post(
                f"/content/{content.id}/conversation",
                json={"message": "First version"},
            )
            assert response1.status_code == 200
            data1 = response1.json()["data"]
            parent_id = data1["conversation_id"]

            # Create branch
            response2 = await client.post(
                f"/content/{content.id}/conversation",
                json={
                    "message": "Second version",
                    "branch_from_id": parent_id,
                },
            )
            assert response2.status_code == 200
            data2 = response2.json()["data"]
            branch_id = data2["conversation_id"]
            assert data2["branch_parent_id"] == parent_id
            assert branch_id != parent_id

            # Verify both conversations exist
            list_response = await client.get(f"/content/{content.id}/conversations")
            assert list_response.status_code == 200
            conversations = list_response.json()["data"]
            assert len(conversations) == 2
            conversation_ids = [c["id"] for c in conversations]
            assert parent_id in conversation_ids
            assert branch_id in conversation_ids
    finally:
        app.dependency_overrides.pop(get_current_user, None)
