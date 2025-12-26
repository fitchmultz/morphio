import pytest


@pytest.mark.asyncio
async def test_health_db_ok(async_client):
    response = await async_client.get("/health/db")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_redis_ok(async_client, monkeypatch):
    async def _ok():
        return True

    monkeypatch.setattr("app.routes.health.test_redis_connection", _ok)
    response = await async_client.get("/health/redis")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_redis_unavailable(async_client, monkeypatch):
    async def _fail():
        return False

    monkeypatch.setattr("app.routes.health.test_redis_connection", _fail)
    response = await async_client.get("/health/redis")
    assert response.status_code == 503
