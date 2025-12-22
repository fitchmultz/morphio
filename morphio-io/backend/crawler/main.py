import logging

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field, HttpUrl

logger = logging.getLogger(__name__)

app = FastAPI(title="Morphio Crawler", version="1.0.0")


class RenderRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL to render and extract text from")


@app.get("/health/")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/render")
async def render(req: RenderRequest) -> dict:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(str(req.url), wait_until="networkidle", timeout=30000)
        body_text = await page.inner_text("body")
        await browser.close()
    text_cleaned = " ".join(body_text.split())
    return {"content": text_cleaned}


if __name__ == "__main__":
    uvicorn.run("backend.crawler.main:app", host="0.0.0.0", port=8002)
