import asyncio
import io
import threading
import time

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient


def test_worker_ml_model_cache_loads_once(monkeypatch):
    from worker_ml.main import app as worker_app
    from worker_ml import model_cache

    model_cache.reset_cache()
    load_calls = {"count": 0}

    async def fake_load(model_name: str, use_mlx: bool):  # noqa: ARG001
        load_calls["count"] += 1

        def _transcriber(file_path: str) -> dict:  # noqa: ARG001
            return {"text": "ok", "confidence": 0.99}

        return _transcriber

    monkeypatch.setattr(model_cache, "_load_transcriber_impl", fake_load)

    client = TestClient(worker_app)
    data = {"file": ("hello.mp3", io.BytesIO(b"fake-bytes"), "audio/mpeg")}
    resp_one = client.post("/transcribe", files=data)
    assert resp_one.status_code == 200

    data_two = {"file": ("hello.mp3", io.BytesIO(b"fake-bytes"), "audio/mpeg")}
    resp_two = client.post("/transcribe", files=data_two)
    assert resp_two.status_code == 200

    assert load_calls["count"] == 1


@pytest.mark.anyio
async def test_worker_ml_max_concurrency(monkeypatch):
    from worker_ml.main import app as worker_app
    import worker_ml.main as worker_mod
    from worker_ml import model_cache

    monkeypatch.setenv("WORKER_ML_MAX_CONCURRENCY", "1")
    monkeypatch.delenv("USE_MLX", raising=False)
    worker_mod._reset_inference_semaphore()
    model_cache.reset_cache()

    lock = threading.Lock()
    in_flight = {"count": 0, "max": 0}

    def fake_transcribe(file_path: str) -> dict:  # noqa: ARG001
        with lock:
            in_flight["count"] += 1
            in_flight["max"] = max(in_flight["max"], in_flight["count"])
        time.sleep(0.1)
        with lock:
            in_flight["count"] -= 1
        return {"text": "ok", "confidence": 0.99}

    model_cache._transcriber = fake_transcribe
    model_cache._cache_key = ("small", False)
    model_cache._model_load_ms = 0

    async with AsyncClient(
        transport=ASGITransport(app=worker_app), base_url="http://test"
    ) as client:

        async def _send() -> None:
            data = {"file": ("hello.mp3", io.BytesIO(b"fake-bytes"), "audio/mpeg")}
            resp = await client.post("/transcribe", files=data)
            assert resp.status_code == 200

        await asyncio.gather(_send(), _send())

    assert in_flight["max"] == 1
