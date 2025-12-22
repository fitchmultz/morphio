import datetime
import hashlib
import json
import logging
from typing import Optional

from redis import asyncio as aioredis
from redis.asyncio import Redis

from ..config import settings
from ..schemas.audio_schema import TranscriptionResult
from ..utils.enums import TranscriptionSource, TranscriptionStatus
from .types import CacheKeyComponent, JsonValue, TranscriptionLike

logger = logging.getLogger(__name__)

# Module-level Redis client with proper typing
_redis_client: Redis | None = None

try:
    _redis_client = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    logger.info("Redis connection established successfully in cache_utils")
except Exception as e:
    logger.error(f"Failed to connect to Redis in cache_utils: {e}")
    _redis_client = None


def _get_redis_client() -> Redis:
    """Get Redis client with type narrowing. Raises if unavailable."""
    if _redis_client is None:
        raise RuntimeError("Redis client is not available")
    return _redis_client


def is_redis_available() -> bool:
    """Check if Redis client is available."""
    return _redis_client is not None


async def test_redis_connection() -> bool:
    """Test Redis connectivity with a set/get operation."""
    if not is_redis_available():
        logger.warning("Redis client not available.")
        return False
    try:
        test_key = "test_connection"
        test_value = "test_value"
        await set_redis_data(test_key, test_value, expire=10)
        retrieved_value = await get_redis_data(test_key)
        if retrieved_value == test_value:
            logger.info("Redis connection test successful (cache_utils)")
            return True
        else:
            logger.error(
                f"Redis connection test failed: retrieved '{retrieved_value}' != '{test_value}'"
            )
            return False
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False


async def get_redis_data(key: str) -> Optional[str]:
    """Retrieve a value from Redis."""
    if not is_redis_available():
        logger.debug(f"Redis not available. Skipping GET for key: {key}")
        return None
    try:
        client = _get_redis_client()
        data = await client.get(key)
        return data
    except aioredis.RedisError as e:
        logger.error(f"Redis error in get_redis_data: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error in get_redis_data: {str(e)}", exc_info=True)
    return None


async def set_redis_data(key: str, value: JsonValue, expire: int = 3600) -> bool:
    """Set a value in Redis."""
    if not is_redis_available():
        logger.debug(f"Redis not available. Skipping SET for key: {key}")
        return False
    try:
        serialized_value = json.dumps(value)
        client = _get_redis_client()
        result = await client.set(key, serialized_value, ex=expire)
        if result:
            logger.debug(f"Successfully set Redis key: {key}")
            return True
        else:
            logger.error(f"Failed to set Redis key: {key}")
            return False
    except aioredis.RedisError as e:
        logger.error(f"Redis error in set_redis_data: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error in set_redis_data: {str(e)}", exc_info=True)
    return False


async def delete_redis_data(key: str) -> bool:
    """Delete a key from Redis."""
    if not is_redis_available():
        logger.debug(f"Redis not available. Skipping DELETE for key: {key}")
        return False
    try:
        client = _get_redis_client()
        result = await client.delete(key)
        if result:
            logger.debug(f"Successfully deleted Redis key: {key}")
            return True
        else:
            logger.debug(f"Redis key not found or not deleted: {key}")
            return False
    except aioredis.RedisError as e:
        logger.error(f"Redis error in delete_redis_data: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error in delete_redis_data: {str(e)}", exc_info=True)
    return False


CACHE_VERSION = "1.0"


def cache_key_builder(prefix: str, *args: CacheKeyComponent) -> str:
    """Build a cache key from multiple arguments."""
    return f"v{CACHE_VERSION}:{prefix}:{':'.join(str(arg) for arg in args)}"


async def get_cache(key: str) -> Optional[str]:
    """Retrieve data from cache."""
    return await get_redis_data(key)


async def set_cache(key: str, value: JsonValue, expire: int = 3600) -> bool:
    """Set data in cache with expiration."""
    if not is_redis_available():
        return False
    try:
        return await set_redis_data(key, value, expire)
    except Exception as e:
        logger.error(f"Error setting cache for key {key}: {e}", exc_info=True)
        return False


async def invalidate_cache(prefix: str, *args: CacheKeyComponent) -> None:
    """Invalidate a specific cache entry."""
    if not is_redis_available():
        return
    key = cache_key_builder(prefix, *args)
    await delete_redis_data(key)
    logger.info(f"Cache invalidated for key: {key}")


async def cache_whisper_transcription(file_hash: str, transcription: TranscriptionLike) -> None:
    """Store Whisper transcription as JSON dict with 'text' field."""
    key = cache_key_builder("whisper_transcription", file_hash, settings.AUDIO_TRANSCRIPTION_MODEL)
    raw_str = serialize_transcription(transcription)
    await set_cache(key, raw_str, expire=604800)


async def get_cached_whisper_transcription(file_hash: str) -> Optional[str]:
    """Retrieve cached Whisper transcription as JSON string."""
    key = cache_key_builder("whisper_transcription", file_hash, settings.AUDIO_TRANSCRIPTION_MODEL)
    return await get_cache(key)


async def cache_youtube_transcript(video_id: str, transcript: TranscriptionLike) -> None:
    """Store YouTube transcription in cache."""
    key = cache_key_builder("youtube_transcript", video_id, settings.AUDIO_TRANSCRIPTION_MODEL)
    raw_str = serialize_transcription(transcript)
    await set_cache(key, raw_str, expire=86400)


async def get_cached_youtube_transcript(video_id: str) -> Optional[str]:
    """Retrieve cached YouTube transcription as JSON string."""
    key = cache_key_builder("youtube_transcript", video_id, settings.AUDIO_TRANSCRIPTION_MODEL)
    return await get_cache(key)


def compute_template_hash(template_content: str) -> str:
    """Compute MD5 hash of template content."""
    return hashlib.md5(template_content.encode("utf-8")).hexdigest()


async def cache_generated_content(
    transcript_hash: str,
    template_id: str,
    template_hash: str,
    user_id: int,
    content: str,
    model_name: str,
) -> None:
    """Cache generated content."""
    key = cache_key_builder(
        "generated_content",
        transcript_hash,
        template_id,
        template_hash,
        user_id,
        model_name,
    )
    await set_cache(key, content, expire=86400)


async def cache_generated_title(content_hash: str, title: str) -> None:
    """Cache generated title by content hash."""
    key = cache_key_builder("generated_title", content_hash)
    await set_cache(key, title, expire=86400)


async def get_cached_generated_title(content_hash: str) -> Optional[str]:
    key = cache_key_builder("generated_title", content_hash)
    return await get_cache(key)


async def get_cached_generated_content(
    transcript_hash: str,
    template_id: str,
    template_hash: str,
    user_id: int,
    model_name: str,
) -> Optional[str]:
    """Retrieve cached generated content."""
    key = cache_key_builder(
        "generated_content",
        transcript_hash,
        template_id,
        template_hash,
        user_id,
        model_name,
    )
    return await get_cache(key)


def serialize_transcription(transcription: TranscriptionLike) -> str:
    """Serialize transcription to JSON string."""
    from .types import HasText, SupportsToDict

    # Check protocols using isinstance (runtime_checkable)
    if isinstance(transcription, str):
        return json.dumps({"text": transcription})
    if isinstance(transcription, SupportsToDict):
        return json.dumps(transcription.to_dict())
    if isinstance(transcription, HasText):
        return json.dumps({"text": transcription.text})
    if hasattr(transcription, "__dict__"):
        return json.dumps(transcription.__dict__)
    return json.dumps({"text": str(transcription)})


async def cache_transcription(
    identifier: str, transcription: TranscriptionResult, source: TranscriptionSource
) -> bool:
    """Unified caching for transcriptions."""
    if (
        not transcription
        or not transcription.text
        or transcription.status in [TranscriptionStatus.FAILED, TranscriptionStatus.INVALID]
    ):
        logger.warning(f"Skipping cache for failed/empty transcription: {identifier}")
        await invalidate_cache(f"{source.value}_transcription", identifier)
        return False

    key = cache_key_builder(
        f"{source.value}_transcription", identifier, settings.AUDIO_TRANSCRIPTION_MODEL
    )
    cache_data = {
        "text": transcription.text,
        "confidence": transcription.confidence,
        "status": (
            transcription.status.value
            if hasattr(transcription.status, "value")
            else transcription.status
        ),
        "source": source.value,
        "metadata": (transcription.metadata if hasattr(transcription, "metadata") else {}),
        "timestamp": datetime.datetime.now().isoformat(),
        "model": settings.AUDIO_TRANSCRIPTION_MODEL,
        "error": transcription.error if hasattr(transcription, "error") else None,
    }
    success = await set_cache(key, cache_data, expire=604800)
    if not success:
        logger.error(f"Failed to cache transcription for {key}")
    else:
        logger.info(f"Successfully cached {source.value} transcription for {identifier}")
    return success


async def get_cached_transcription(
    identifier: str, source: TranscriptionSource
) -> Optional[TranscriptionResult]:
    """Get cached transcription as a TranscriptionResult."""
    key = cache_key_builder(
        f"{source.value}_transcription", identifier, settings.AUDIO_TRANSCRIPTION_MODEL
    )
    try:
        cached_data = await get_cache(key)
        if not cached_data:
            return None
        data = json.loads(cached_data)
        if isinstance(data, str):
            logger.warning("Found plain string for transcription, ignoring.")
            return None
        return TranscriptionResult(
            text=data.get("text", ""),
            confidence=data.get("confidence"),
            status=TranscriptionStatus(data.get("status", TranscriptionStatus.FAILED.value)),
            source=source,
            error=data.get("error"),
        )
    except Exception as e:
        logger.error(f"Error retrieving cached transcription: {e}")
        return None
