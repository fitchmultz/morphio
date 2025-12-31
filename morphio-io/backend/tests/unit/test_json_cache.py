import json

import pytest

from app.utils import json_cache


@pytest.mark.asyncio
async def test_get_or_set_json_single_load(monkeypatch):
    store: dict[str, str] = {}

    async def fake_get(key: str):
        return store.get(key)

    async def fake_set(key: str, value, expire: int = 3600):
        store[key] = json.dumps(value)
        return True

    monkeypatch.setattr(json_cache, "get_redis_data", fake_get)
    monkeypatch.setattr(json_cache, "set_redis_data", fake_set)
    monkeypatch.setattr(json_cache, "is_redis_available", lambda: True)

    calls = {"count": 0}

    async def loader():
        calls["count"] += 1
        return {"status": "ok"}

    result_1 = await json_cache.get_or_set_json("templates:list:v1", 60, loader)
    result_2 = await json_cache.get_or_set_json("templates:list:v1", 60, loader)

    assert result_1 == {"status": "ok"}
    assert result_2 == {"status": "ok"}
    assert calls["count"] == 1
