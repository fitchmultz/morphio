"""Purpose: Implement web scraping and downstream content-generation workflows.
Responsibilities: Fetch web content, normalize extracted text, and support generation-oriented web operations.
Scope: Backend service-layer helpers used by higher-level web processing flows.
Usage: Imported by route and service modules that orchestrate web content ingestion.
Invariants/Assumptions: Optional browser dependencies remain explicitly typed and failures are surfaced through service errors.
"""

import importlib
import json
import logging
from typing import Any, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...utils.cache_utils import (
    cache_generated_content,
    compute_template_hash,
    get_cached_generated_content,
)
from ...utils.enums import JobStatus, ProcessingStage, UsageType
from ...utils.error_handlers import ApplicationException
from ...utils.file_utils import compute_hash
from ..generation import generate_content_from_transcript, save_generated_content
from ..job import get_job_status, update_job_status
from ..template import get_template_by_name, load_template
from ..usage import increment_usage
from .validation import is_private_or_local_address

logger = logging.getLogger(__name__)


async def scrape_webpage(url: str) -> str:
    """
    Use Playwright to load URL, wait for JS, and return body text.

    :param url: The URL to scrape
    :return: Cleaned text content from the web page
    :raises ApplicationException: If URL resolves to private/local address or if scraped
        text is too short
    """
    logger.info(f"Scraping webpage URL={url}")
    if is_private_or_local_address(url):
        raise ApplicationException(
            "Scraping private/local/internal addresses is disallowed", status_code=400
        )

    # Prefer external crawler service if configured
    if settings.CRAWLER_URL:
        try:
            timeout = httpx.Timeout(settings.SERVICE_TIMEOUT)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{settings.CRAWLER_URL.rstrip('/')}/render",
                    json={"url": url},
                )
                resp.raise_for_status()
                data = resp.json()
                body_text: Optional[str] = data.get("content")
                if not body_text:
                    raise ApplicationException("Crawler returned no content", 502)
        except Exception as e:
            logger.error(f"Remote crawler error: {e}")
            raise ApplicationException("Crawler service failed", 502)
    else:
        # Local fallback using Playwright (requires crawler deps)
        try:
            playwright_async_api = importlib.import_module("playwright.async_api")
            async_playwright: Any = getattr(playwright_async_api, "async_playwright", None)
            if async_playwright is None:
                raise ImportError("playwright.async_api.async_playwright is unavailable")
        except Exception as e:  # pragma: no cover
            logger.error(f"Playwright not available: {e}")
            raise ApplicationException("Crawler not available", 501)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            body_text = await page.inner_text("body")
            await browser.close()

    text_cleaned = " ".join(body_text.split()) if body_text else ""
    if not text_cleaned or len(text_cleaned) < 30:
        raise ApplicationException(
            "Scraped text is empty or too short to be useful", status_code=400
        )
    return text_cleaned


async def scrape_and_generate_web(
    input_data: dict,
    job_id: str,
    db: AsyncSession,
    user_id: int,
) -> None:
    """Scrape webpage and generate content from the text."""
    url = input_data["url"]
    template_id = input_data["template_id"]

    try:
        # Get model_name from JobStatusInfo via job_id
        job_status = await get_job_status(job_id)
        chosen_model = getattr(job_status, "chosen_model", None) or settings.CONTENT_MODEL

        logger.debug(f"Using model: {chosen_model} for job {job_id}")

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            10,
            "Scraping webpage",
            stage=ProcessingStage.DOWNLOADING,
        )
        await increment_usage(db, user_id, UsageType.WEB_SCRAPING)
        scraped_text = await scrape_webpage(url)

        if isinstance(template_id, str) and template_id.isdigit():
            template_id_val = int(template_id)
        elif isinstance(template_id, str):
            tmp = await get_template_by_name(db, template_id)
            if tmp is None:
                raise ApplicationException("Template not found", 404)
            template_id_val = tmp
        else:
            template_id_val = int(template_id)

        template_content = await load_template(template_id_val, db)
        template_hash = compute_template_hash(template_content)

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            40,
            "Template loaded",
            stage=ProcessingStage.DOWNLOADING,
        )

        transcript_hash = compute_hash(scraped_text)
        cached_content = await get_cached_generated_content(
            transcript_hash,
            str(template_id_val),
            template_hash,
            user_id,
            chosen_model,
        )

        if cached_content:
            generated_content = json.loads(cached_content)
            logger.info("Cache hit for web content generation.")
        else:
            await update_job_status(
                job_id,
                JobStatus.PROCESSING.value,
                60,
                "Generating content",
                stage=ProcessingStage.GENERATING,
            )
            generated_content = await generate_content_from_transcript(
                transcript=scraped_text,
                template_content=template_content,
                chosen_model=chosen_model,
            )
            generated_content += f"\n\nSource: [{url}]({url})"
            await cache_generated_content(
                transcript_hash,
                str(template_id_val),
                template_hash,
                user_id,
                json.dumps(generated_content),
                chosen_model,
            )

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            80,
            "Saving content",
            stage=ProcessingStage.SAVING,
        )
        saved = await save_generated_content(generated_content, user_id)
        if not saved or not saved.id:
            raise ApplicationException("Could not save content", 500)

        result = {
            "content": saved.content,
            "title": saved.title,
            "content_id": saved.id,
            "user_id": user_id,
            "template_id": template_id_val,
        }
        await update_job_status(
            job_id,
            JobStatus.COMPLETED.value,
            100,
            "Web scraping + generation complete",
            result=result,
            stage=ProcessingStage.COMPLETED,
        )

    except ApplicationException as ae:
        logger.error(f"Application error in scrape_and_generate_web: {ae.message}")
        await update_job_status(
            job_id,
            JobStatus.FAILED.value,
            100,
            f"Error: {ae.message}",
            error=ae.message,
            stage=ProcessingStage.FAILED,
        )
    except Exception as e:
        logger.error(f"Unexpected error in scrape_and_generate_web: {str(e)}", exc_info=True)
        await update_job_status(
            job_id,
            JobStatus.FAILED.value,
            100,
            f"Unexpected error: {str(e)}",
            error=str(e),
            stage=ProcessingStage.FAILED,
        )
