import io

import importlib.util

import pytest
from fastapi.testclient import TestClient

# Check if playwright is available (crawler dependency)
_playwright_available = importlib.util.find_spec("playwright") is not None


def test_worker_ml_transcribe_mocked():
    # Import worker app and monkeypatch the heavy transcribe
    from worker_ml.main import app as worker_app
    import worker_ml.main as worker_mod

    async def fake_transcribe(path: str, model: str):
        return {"text": "hello world", "confidence": 0.99}

    worker_mod._transcribe = fake_transcribe  # type: ignore[attr-defined]

    client = TestClient(worker_app)
    data = {"file": ("hello.mp3", io.BytesIO(b"fake-bytes"), "audio/mpeg")}
    resp = client.post("/transcribe", files=data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["text"] == "hello world"


@pytest.mark.skipif(not _playwright_available, reason="Playwright not installed")
def test_crawler_render_mocked():
    from unittest.mock import patch
    from crawler.main import app as crawler_app

    class _FakePage:
        async def inner_text(self, selector: str) -> str:  # noqa: ARG002
            return "Rendered Content"

        async def goto(self, url: str, wait_until: str = "networkidle", timeout: int = 30000):  # noqa: ARG002
            return None

    class _FakeBrowser:
        async def new_page(self):
            return _FakePage()

        async def close(self):
            return None

    class _FakeChromium:
        async def launch(self, headless: bool = True):  # noqa: ARG002
            return _FakeBrowser()

    class _FakePlaywright:
        @property
        def chromium(self):
            return _FakeChromium()

    class _AsyncCtx:
        async def __aenter__(self):
            return _FakePlaywright()

        async def __aexit__(self, exc_type, exc, tb):  # noqa: ARG002
            return False

    def fake_async_playwright():
        # Return the context manager directly, not a coroutine
        return _AsyncCtx()

    # Patch where it's imported inside the function
    with patch("playwright.async_api.async_playwright", fake_async_playwright):
        client = TestClient(crawler_app)
        resp = client.post("/render", json={"url": "https://example.com"})
        assert resp.status_code == 200
        assert resp.json()["content"] == "Rendered Content"
