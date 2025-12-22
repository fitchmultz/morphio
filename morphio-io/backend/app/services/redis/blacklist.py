import logging

from ...utils.cache_utils import (
    cache_key_builder,
    delete_redis_data,
    get_cache,
    set_cache,
)
from ...utils.security_logger import redact_token_id

logger = logging.getLogger(__name__)


async def add_to_token_blacklist(token_id: str, expiry_seconds: int) -> bool:
    """
    Add a token to the blacklist with an expiry.
    Returns True if successful, False otherwise.

    :param token_id: The token ID to blacklist
    :param expiry_seconds: The time in seconds after which the token will be removed from blacklist
    :return: True if successful, False otherwise
    """
    try:
        key = cache_key_builder("blacklist", token_id)
        result = await set_cache(key, "1", expire=expiry_seconds)
        logger.debug(
            f"Token {redact_token_id(token_id)} added to blacklist for {expiry_seconds} seconds"
        )
        return result
    except Exception as e:
        logger.error(f"Failed to add token to blacklist: {str(e)}", exc_info=True)
        return False


async def is_token_blacklisted(token_id: str, fail_closed: bool = True) -> bool:
    """
    Check if a token is in the blacklist.
    Returns True if blacklisted, False otherwise.

    :param token_id: The token ID to check
    :param fail_closed: If True, treat Redis errors as "token is blacklisted" (secure default)
    :return: True if blacklisted, False otherwise
    """
    try:
        key = cache_key_builder("blacklist", token_id)
        result = await get_cache(key)
        return result is not None
    except Exception as e:
        logger.error(f"Failed to check token blacklist: {str(e)}", exc_info=True)
        # Fail-closed: treat Redis errors as blacklisted for security
        # This prevents revoked tokens from being used if Redis is down
        if fail_closed:
            logger.warning("Redis unavailable - treating token as blacklisted (fail-closed)")
            return True
        return False


async def remove_from_token_blacklist(token_id: str) -> bool:
    """
    Remove a token from the blacklist (if needed for testing or management).
    Returns True if successful, False otherwise.

    :param token_id: The token ID to remove from blacklist
    :return: True if successful, False otherwise
    """
    try:
        key = cache_key_builder("blacklist", token_id)
        result = await delete_redis_data(key)
        logger.debug(f"Token {redact_token_id(token_id)} removed from blacklist: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to remove token from blacklist: {str(e)}", exc_info=True)
        return False
