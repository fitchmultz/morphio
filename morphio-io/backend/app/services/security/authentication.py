import logging
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import ExpiredSignatureError, PyJWTError as JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...models.user import User
from ...schemas.security_schema import PasswordComplexity
from ...utils.error_handlers import ApplicationException, handle_application_exception
from ...utils.security_logger import (
    SECURITY_ALERT,
    SECURITY_AUDIT,
    SecurityEventType,
    log_security_event,
)

logger = logging.getLogger(__name__)

# Create OAuth2 scheme with auto_error=False for optional auth support
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if the provided plain password matches the hashed password.

    :param plain_password: The plain text password
    :param hashed_password: The hashed password
    :return: True if the passwords match, False otherwise
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        # Never log password hashes - security sensitive material
        log_security_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            message="Error verifying password hash",
            level=SECURITY_ALERT,
            details={"error": str(e)},
        )
        return False


def get_password_hash(password: str) -> str:
    """
    Hash the provided password.

    :param password: The plain text password
    :return: The hashed password
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def is_password_complex(password: str) -> bool:
    """
    Check if the password meets complexity requirements.

    :param password: The password to check
    :return: True if the password is complex enough, raises exception otherwise
    """
    complexity = PasswordComplexity(
        min_length=8,
        require_upper=True,
        require_lower=True,
        require_digit=True,
        require_special=True,
        special_chars='!@#$%^&*(),.?":{}|<>',
    )
    if len(password) < complexity.min_length:
        log_security_event(
            event_type=SecurityEventType.PASSWORD_CHANGE,
            message="Password complexity check failed - insufficient length",
            level=SECURITY_AUDIT,
        )
        raise ApplicationException(
            message="Password must contain at least 8 characters, including uppercase, "
            "lowercase, numbers, and special characters",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    has_upper = any(char.isupper() for char in password) if complexity.require_upper else True
    has_lower = any(char.islower() for char in password) if complexity.require_lower else True
    has_digit = any(char.isdigit() for char in password) if complexity.require_digit else True
    has_special = (
        any(char in complexity.special_chars for char in password)
        if complexity.require_special
        else True
    )

    if not (has_upper and has_lower and has_digit and has_special):
        log_security_event(
            event_type=SecurityEventType.PASSWORD_CHANGE,
            message="Password complexity check failed - missing required character types",
            level=SECURITY_AUDIT,
            details={
                "has_upper": has_upper,
                "has_lower": has_lower,
                "has_digit": has_digit,
                "has_special": has_special,
            },
        )
        raise ApplicationException(
            message="Password must contain at least one uppercase letter, one lowercase "
            "letter, one digit, and one special character",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return True


async def _authenticate_api_key(token: str, db: AsyncSession) -> Optional[User]:
    """
    Attempt to authenticate using an API key.

    :param token: The API key (must start with "mio_")
    :param db: The database session
    :return: The authenticated user or None if not an API key
    """

    from ...models.api_key import APIKey
    from ...utils.response_utils import utc_now

    if not token.startswith("mio_"):
        return None

    # Hash the key and look it up
    hashed_key = APIKey.verify_key(token)
    result = await db.execute(
        select(APIKey).where(
            APIKey.hashed_key == hashed_key,
            APIKey.deleted_at.is_(None),
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        log_security_event(
            event_type=SecurityEventType.ACCESS_DENIED,
            message="Invalid API key used for authentication",
            level=SECURITY_AUDIT,
            details={"key_prefix": token[:12] if len(token) >= 12 else token},
        )
        raise ApplicationException(
            message="Invalid API key",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Update last_used_at
    api_key.last_used_at = utc_now()
    await db.commit()

    # Get the user
    user = await db.scalar(select(User).where(User.id == api_key.user_id))
    if not user:
        log_security_event(
            event_type=SecurityEventType.ACCESS_DENIED,
            message="User for API key not found",
            level=SECURITY_AUDIT,
            details={"key_prefix": api_key.key_prefix},
        )
        raise ApplicationException(
            message="User not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    log_security_event(
        event_type="API_KEY_VALIDATED",
        message="User successfully authenticated via API key",
        level=SECURITY_AUDIT,
        user_id=int(user.id),
        details={"key_prefix": api_key.key_prefix},
    )
    return user


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from the token or API key.

    Supports both JWT tokens and API keys (format: mio_*).

    :param token: The access token or API key (may be None if auto_error=False)
    :param db: The database session
    :return: The authenticated user
    """
    # Handle missing token (since oauth2_scheme has auto_error=False)
    if not token:
        raise ApplicationException(
            message="Not authenticated",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Try API key authentication first
    if token.startswith("mio_"):
        user = await _authenticate_api_key(token, db)
        if user:
            return user

    # Fall back to JWT authentication
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id_val = payload.get("sub")
        token_type_val = payload.get("type")
        if not isinstance(user_id_val, str) or not isinstance(token_type_val, str):
            log_security_event(
                event_type=SecurityEventType.ACCESS_DENIED,
                message="Invalid token payload types",
                level=SECURITY_AUDIT,
            )
            raise ApplicationException(
                message="Invalid authentication credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        user_id: str = user_id_val
        token_type: str = token_type_val

        if user_id is None or token_type != "access":
            log_security_event(
                event_type=SecurityEventType.ACCESS_DENIED,
                message="Invalid token: missing subject or wrong token type",
                level=SECURITY_AUDIT,
                details={"token_type": token_type},
            )
            raise ApplicationException(
                message="Invalid authentication credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        user = await db.scalar(select(User).where(User.id == int(user_id)))
        if user is None:
            log_security_event(
                event_type=SecurityEventType.ACCESS_DENIED,
                message="User from token not found in database",
                level=SECURITY_AUDIT,
                user_id=user_id,
            )
            raise ApplicationException(
                message="User not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Log successful token validation
        log_security_event(
            event_type="TOKEN_VALIDATED",
            message="User successfully authenticated via token",
            level=SECURITY_AUDIT,
            user_id=int(user.id),
        )
        return user
    except ExpiredSignatureError:
        log_security_event(
            event_type=SecurityEventType.ACCESS_DENIED,
            message="Expired token used for authentication",
            level=SECURITY_AUDIT,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except JWTError:
        log_security_event(
            event_type=SecurityEventType.ACCESS_DENIED,
            message="Invalid JWT token",
            level=SECURITY_AUDIT,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}", exc_info=True)
        log_security_event(
            event_type=SecurityEventType.ACCESS_DENIED,
            message=f"Unexpected error in authentication: {str(e)}",
            level=SECURITY_ALERT,
        )
        raise handle_application_exception(e)


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user if a valid token is provided, otherwise return None.

    :param token: The access token (optional)
    :param db: The database session
    :return: The authenticated user or None
    """
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except ApplicationException:
        return None
