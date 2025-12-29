import uuid

from sqlalchemy import select

from app.models.user import User
from app.utils.enums import UserRole


async def _register_user(async_client):
    user_data = {
        "email": f"admin-health-{uuid.uuid4()}@example.com",
        "password": "StrongP@ssw0rd123!",
        "display_name": "Admin Health Tester",
    }
    response = await async_client.post("/auth/register", json=user_data)
    assert response.status_code == 200, response.json()
    return response.json()["data"]["access_token"], user_data["email"]


async def _promote_to_admin(db_session, email: str) -> None:
    user = await db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.role = UserRole.ADMIN
    await db_session.commit()


async def test_admin_health_rejects_non_admin(async_client):
    access_token, _email = await _register_user(async_client)
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await async_client.get("/admin/health", headers=headers)

    assert response.status_code == 403


async def test_admin_health_returns_component_statuses(async_client, db_session):
    access_token, email = await _register_user(async_client)
    await _promote_to_admin(db_session, email)
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await async_client.get("/admin/health", headers=headers)

    assert response.status_code == 200, response.json()
    payload = response.json()
    assert payload["status"] == "success"
    components = payload["data"]["components"]
    assert "database" in components
    assert "redis" in components
    assert "worker_ml" in components
    assert "crawler" in components
    assert components["database"]["status"] == "ok"
    assert components["worker_ml"]["status"] == "skipped"
    assert components["crawler"]["status"] == "skipped"
