import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from .cache_utils import delete_redis_data, get_redis_data, is_redis_available, set_redis_data

logger = logging.getLogger(__name__)

_lock_guard = asyncio.Lock()
_key_locks: dict[str, asyncio.Lock] = {}


async def _get_key_lock(key: str) -> asyncio.Lock:
    async with _lock_guard:
        lock = _key_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _key_locks[key] = lock
        return lock


async def get_or_set_json(key: str, ttl_s: int, loader: Callable[[], Awaitable[Any]]) -> Any:
    if not is_redis_available():
        return await loader()

    try:
        cached = await get_redis_data(key)
        if cached is not None:
            return json.loads(cached)
    except Exception:
        logger.warning("Redis read failed for key %s; bypassing cache", key, exc_info=True)
        return await loader()

    lock = await _get_key_lock(key)
    async with lock:
        try:
            cached = await get_redis_data(key)
            if cached is not None:
                return json.loads(cached)
        except Exception:
            logger.warning(
                "Redis read failed during single-flight for key %s; bypassing cache",
                key,
                exc_info=True,
            )
            return await loader()

        value = await loader()
        try:
            await set_redis_data(key, value, expire=ttl_s)
        except Exception:
            logger.warning("Redis write failed for key %s; continuing", key, exc_info=True)
        return value


async def delete(key: str) -> None:
    if not is_redis_available():
        return
    try:
        await delete_redis_data(key)
    except Exception:
        logger.warning("Redis delete failed for key %s; continuing", key, exc_info=True)


async def delete_many(keys: list[str]) -> None:
    if not is_redis_available():
        return
    for key in keys:
        try:
            await delete_redis_data(key)
        except Exception:
            logger.warning("Redis delete failed for key %s; continuing", key, exc_info=True)
