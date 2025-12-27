"""Log processing functionality for analyzing logs and generating summaries/configs."""

import hashlib
import json
import logging
import os
from pathlib import Path

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from ...config import settings
from ...schemas.logs_schema import LogsProcessingStatusResponse
from ...services.generation import (
    generate_content_from_transcript,
    save_generated_content,
)
from ...services.job import get_job_status, update_job_status
from ...services.template import load_template
from ...services.usage import increment_usage
from ...adapters.anonymizer import anonymize_content, deanonymize_content
from ...utils.cache_utils import (
    cache_generated_content,
    compute_template_hash,
    get_cached_generated_content,
)
from ...utils.enums import JobStatus, ProcessingStage, UsageType
from ...utils.error_handlers import ApplicationException
from ...utils.file_utils import compute_file_hash
from ...utils.job_utils import enqueue_task

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def process_logs_file(
    input_data: dict,
    job_id: str,
    db: AsyncSession,
    user_id: int,
) -> None:
    """
    Process a log file and generate a summary asynchronously.

    Args:
        input_data: Dictionary containing file_path and anonymize flag
        job_id: The job ID for tracking progress
        db: Database session
        user_id: The user ID

    Returns:
        None
    """
    file_path = Path(input_data["file_path"])
    anonymize = input_data.get("anonymize", False)
    try:
        # Get model_name from JobStatusInfo via job_id
        job_status = await get_job_status(job_id)
        chosen_model = getattr(job_status, "chosen_model", None) or settings.CONTENT_MODEL

        logger.debug(f"Using model: {chosen_model} for job {job_id}")

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            10,
            "Reading log file",
            stage=ProcessingStage.DOWNLOADING,
        )

        # Validate file existence
        if not file_path.exists():
            raise ApplicationException(f"Log file not found: {file_path}", 404)

        # Read the raw log content
        async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_logs = await f.read()

        if not raw_logs.strip():
            raise ApplicationException("Log file is empty", 400)

        await increment_usage(db, user_id, UsageType.LOG_PROCESSING)
        file_hash = await compute_file_hash(str(file_path))

        # Anonymize content if enabled
        processed_logs = anonymize_content(raw_logs, anonymize)

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            30,
            "Loading template",
            stage=ProcessingStage.DOWNLOADING,
        )
        template_content = await load_template("log-summary", db)
        if not template_content:
            raise ApplicationException("Template 'log-summary' not found", 404)
        template_hash = compute_template_hash(template_content)

        transcript_hash = hashlib.md5(processed_logs.encode()).hexdigest()
        cached_content = await get_cached_generated_content(
            transcript_hash, "log-summary", template_hash, user_id, chosen_model
        )

        if cached_content:
            generated_summary = json.loads(cached_content)
            logger.info(f"Cache hit for log summary: {file_hash}")
        else:
            await update_job_status(
                job_id,
                JobStatus.PROCESSING.value,
                50,
                "Generating summary",
                stage=ProcessingStage.GENERATING,
            )
            generated_summary = await generate_content_from_transcript(
                transcript=processed_logs,
                template_content=template_content,
                chosen_model=chosen_model,
            )
            await cache_generated_content(
                transcript_hash,
                "log-summary",
                template_hash,
                user_id,
                json.dumps(generated_summary),
                chosen_model,
            )

        # De-anonymize the summary if anonymization was enabled
        final_summary = deanonymize_content(generated_summary, processed_logs, anonymize)

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            70,
            "Saving generated content",
            stage=ProcessingStage.SAVING,
        )
        saved_content = await save_generated_content(final_summary, user_id)

        result = {
            "summary": saved_content.content,
            "title": saved_content.title,
            "content_id": saved_content.id,
            "user_id": user_id,
            "template_id": "log-summary",
        }

        await update_job_status(
            job_id,
            JobStatus.COMPLETED.value,
            100,
            "Log summary generated and saved",
            result=result,
            stage=ProcessingStage.COMPLETED,
        )

    except ApplicationException as e:
        logger.error(f"Application error in log processing: {e.message}")
        await update_job_status(
            job_id,
            JobStatus.FAILED.value,
            100,
            f"Error: {e.message}",
            error=e.message,
            stage=ProcessingStage.FAILED,
        )
    except Exception as e:
        logger.error(f"Unexpected error in log processing: {str(e)}", exc_info=True)
        await update_job_status(
            job_id,
            JobStatus.FAILED.value,
            100,
            f"Unexpected error: {str(e)}",
            error=str(e),
            stage=ProcessingStage.FAILED,
        )
    finally:
        # Clean up the file
        if file_path.exists():
            try:
                os.unlink(file_path)
            except OSError as e:
                logger.warning(f"Failed to delete file {file_path}: {e}")


async def enqueue_logs_processing(
    file_path: Path,
    user_id: int,
    db: AsyncSession,
    model_name: str = "",
    anonymize: bool = False,
) -> str:
    """
    Enqueue a log processing task.

    Args:
        file_path: Path to the log file
        user_id: The user ID
        db: Database session
        model_name: Model to use for generation (optional)
        anonymize: Whether to anonymize sensitive information

    Returns:
        str: The job ID

    Raises:
        ApplicationException: If user ID is missing
    """
    if not user_id:
        raise ApplicationException("User ID is required", 400)
    input_data = {
        "file_path": str(file_path),
        "db": db,
        "anonymize": anonymize,
    }
    return await enqueue_task(process_logs_file, input_data, db, user_id, model_name)


async def get_logs_processing_status(
    job_id: str, user_id: int, db: AsyncSession
) -> LogsProcessingStatusResponse:
    """
    Retrieve the status of a log processing job.

    Args:
        job_id: The job ID
        user_id: The user ID
        db: Database session

    Returns:
        LogsProcessingStatusResponse: Job status information

    Raises:
        ApplicationException: If user is not authorized to access this job
    """
    status = await get_job_status(job_id)
    if status.user_id != user_id:
        raise ApplicationException("Not authorized to access this job", status_code=403)
    return LogsProcessingStatusResponse(
        job_id=job_id,
        status=status.status,
        progress=status.progress,
        stage=status.stage,
        message=status.message,
        result=status.result,
        error=status.error,
    )


async def process_splunk_config(
    input_data: dict,
    job_id: str,
    db: AsyncSession,
    user_id: int,
) -> None:
    """
    Process a log sample and generate Splunk configuration files.

    Args:
        input_data: Dictionary containing file_path and anonymize flag
        job_id: The job ID for tracking progress
        db: Database session
        user_id: The user ID

    Returns:
        None
    """
    file_path = Path(input_data["file_path"])
    anonymize = input_data.get("anonymize", False)
    try:
        # Get model_name from JobStatusInfo via job_id
        job_status = await get_job_status(job_id)
        chosen_model = getattr(job_status, "chosen_model", None) or settings.CONTENT_MODEL

        logger.debug(f"Using model: {chosen_model} for job {job_id}")

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            10,
            "Reading log sample",
            stage=ProcessingStage.DOWNLOADING,
        )

        if not file_path.exists():
            raise ApplicationException(f"Log file not found: {file_path}", 404)

        async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_logs = await f.read()

        if not raw_logs.strip():
            raise ApplicationException("Log sample is empty", 400)

        await increment_usage(db, user_id, UsageType.LOG_PROCESSING)
        file_hash = await compute_file_hash(str(file_path))

        processed_logs = anonymize_content(raw_logs, anonymize)

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            30,
            "Loading Splunk config template",
            stage=ProcessingStage.DOWNLOADING,
        )
        template_content = await load_template("splunk-config", db)
        if not template_content:
            raise ApplicationException("Template 'splunk-config' not found", 404)
        template_hash = compute_template_hash(template_content)

        transcript_hash = hashlib.md5(processed_logs.encode()).hexdigest()
        cached_content = await get_cached_generated_content(
            transcript_hash, "splunk-config", template_hash, user_id, chosen_model
        )

        if cached_content:
            splunk_config = json.loads(cached_content)
            logger.info(f"Cache hit for Splunk config: {file_hash}")
        else:
            await update_job_status(
                job_id,
                JobStatus.PROCESSING.value,
                50,
                "Generating Splunk config",
                stage=ProcessingStage.GENERATING,
            )
            splunk_config = await generate_content_from_transcript(
                transcript=processed_logs,
                template_content=template_content,
                chosen_model=chosen_model,
            )
            await cache_generated_content(
                transcript_hash,
                "splunk-config",
                template_hash,
                user_id,
                json.dumps(splunk_config),
                chosen_model,
            )

        final_config = deanonymize_content(splunk_config, processed_logs, anonymize)

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            70,
            "Saving Splunk config",
            stage=ProcessingStage.SAVING,
        )
        saved_content = await save_generated_content(final_config, user_id)

        result = {
            "content": saved_content.content,
            "title": saved_content.title,
            "content_id": saved_content.id,
            "user_id": user_id,
            "template_id": "splunk-config",
        }

        await update_job_status(
            job_id,
            JobStatus.COMPLETED.value,
            100,
            "Splunk configuration generated and saved",
            result=result,
            stage=ProcessingStage.COMPLETED,
        )

    except ApplicationException as e:
        logger.error(f"Application error in Splunk config generation: {e.message}")
        await update_job_status(
            job_id,
            JobStatus.FAILED.value,
            100,
            f"Error: {e.message}",
            error=e.message,
            stage=ProcessingStage.FAILED,
        )
    except Exception as e:
        logger.error(f"Unexpected error in Splunk config generation: {str(e)}", exc_info=True)
        await update_job_status(
            job_id,
            JobStatus.FAILED.value,
            100,
            f"Unexpected error: {str(e)}",
            error=str(e),
            stage=ProcessingStage.FAILED,
        )
    finally:
        if file_path.exists():
            try:
                os.unlink(file_path)
            except OSError as e:
                logger.warning(f"Failed to delete file {file_path}: {e}")


async def enqueue_splunk_config_processing(
    file_path: Path,
    user_id: int,
    db: AsyncSession,
    model_name: str = "",
    anonymize: bool = False,
) -> str:
    """
    Enqueue a Splunk config generation task.

    Args:
        file_path: Path to the log file
        user_id: The user ID
        db: Database session
        model_name: Model to use for generation (optional)
        anonymize: Whether to anonymize sensitive information

    Returns:
        str: The job ID

    Raises:
        ApplicationException: If user ID is missing
    """
    if not user_id:
        raise ApplicationException("User ID is required", 400)
    input_data = {
        "file_path": str(file_path),
        "db": db,
        "anonymize": anonymize,
    }
    return await enqueue_task(process_splunk_config, input_data, db, user_id, model_name)
