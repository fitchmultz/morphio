import logging
import secrets
from datetime import timedelta

from fastapi import status
import jwt
from jwt.exceptions import ExpiredSignatureError, PyJWTError as JWTError

from ...config import settings
from ...models.user import User
from ...schemas.security_schema import TokenPayload
from ...utils.error_handlers import ApplicationException
from ...utils.response_utils import utc_now
from ...utils.security_logger import (
    SECURITY_ALERT,
    SECURITY_AUDIT,
    log_security_event,
    redact_token_id,
)

logger = logging.getLogger(__name__)


def create_token(data: dict, token_type: str) -> str:
    """
    Create a new token (access or refresh).

    :param data: The data to encode in the token
    :param token_type: The type of token ("access" or "refresh")
    :return: The encoded JWT token
    """
    to_encode = data.copy()
    if token_type == "access":
        expire = utc_now() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    elif token_type == "refresh":
        expire = utc_now() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        raise ValueError("Invalid token type")

    # Add token ID if not present
    if "jti" not in to_encode:
        to_encode["jti"] = secrets.token_hex(16)

    # Create the token payload
    payload = {
        "sub": to_encode.get("sub"),
        "exp": expire,
        "iat": utc_now(),
        "type": token_type,
        "jti": to_encode.get("jti"),
    }

    # Add token family for refresh tokens
    if token_type == "refresh" and "family" in to_encode:
        payload["family"] = to_encode.get("family")

    try:
        encoded_jwt = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        logger.debug(f"{token_type.capitalize()} token created for user: {to_encode.get('sub')}")

        # Log token creation
        log_security_event(
            event_type="TOKEN_CREATED",
            message=f"{token_type.capitalize()} token created",
            level=SECURITY_AUDIT,
            user_id=to_encode.get("sub"),
            details={
                "token_type": token_type,
                "token_id": redact_token_id(to_encode.get("jti")),
                "family": (
                    redact_token_id(to_encode.get("family"))
                    if token_type == "refresh" and "family" in to_encode
                    else None
                ),
                "expires_at": expire.isoformat(),
            },
        )

        return encoded_jwt
    except Exception as e:
        logger.error(f"Error encoding JWT: {str(e)}", exc_info=True)

        # Log token creation failure
        log_security_event(
            event_type="TOKEN_CREATION_FAILED",
            message=f"Failed to create {token_type} token",
            level=SECURITY_ALERT,
            user_id=to_encode.get("sub"),
            details={"error": str(e)},
        )

        raise ApplicationException(
            message=f"Failed to create {token_type} token. Please try again.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Create an access token.

    :param data: The data to encode in the token
    :param expires_delta: Optional custom expiration time
    :return: The encoded access token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access", "iat": utc_now()})

    # Add token ID if not present
    if "jti" not in to_encode:
        to_encode["jti"] = secrets.token_hex(16)

    # Ensure we're using the user's ID, not email
    if "sub" in to_encode and isinstance(to_encode["sub"], User):
        to_encode["sub"] = str(to_encode["sub"].id)
    elif "sub" in to_encode and isinstance(to_encode["sub"], str):
        # If it's already a string, assume it's the user ID
        pass
    else:
        error_msg = "Invalid subject for token"

        # Log token creation failure
        log_security_event(
            event_type="TOKEN_CREATION_FAILED",
            message=error_msg,
            level=SECURITY_ALERT,
            details={"error": error_msg},
        )

        raise ValueError(error_msg)

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # Log access token creation
    log_security_event(
        event_type="ACCESS_TOKEN_CREATED",
        message="Access token created",
        level=SECURITY_AUDIT,
        user_id=to_encode.get("sub"),
        details={
            "token_id": redact_token_id(to_encode.get("jti")),
            "expires_at": expire.isoformat(),
            "custom_expiry": expires_delta is not None,
        },
    )

    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    """
    Create a refresh token.

    :param data: The data to encode in the token
    :param expires_delta: Optional custom expiration time
    :return: The encoded refresh token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "iat": utc_now()})

    # Add token ID if not present
    if "jti" not in to_encode:
        to_encode["jti"] = secrets.token_hex(16)

    # Add token family if not present (for refresh token rotation)
    if "family" not in to_encode:
        to_encode["family"] = secrets.token_hex(8)

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # Log refresh token creation
    log_security_event(
        event_type="REFRESH_TOKEN_CREATED",
        message="Refresh token created",
        level=SECURITY_AUDIT,
        user_id=to_encode.get("sub"),
        details={
            "token_id": redact_token_id(to_encode.get("jti")),
            "family": redact_token_id(to_encode.get("family")),
            "expires_at": expire.isoformat(),
            "custom_expiry": expires_delta is not None,
        },
    )

    return encoded_jwt


def verify_token(token: str, token_type: str) -> TokenPayload:
    """
    Verify and decode a token.

    :param token: The token to verify
    :param token_type: The expected token type
    :return: The decoded token payload
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_data = TokenPayload(**payload)

        # Verify token type
        if token_data.type != token_type:
            log_security_event(
                event_type="TOKEN_VERIFICATION_FAILED",
                message=f"Invalid token type: expected {token_type}, got {token_data.type}",
                level=SECURITY_AUDIT,
                user_id=token_data.sub,
                details={
                    "expected_type": token_type,
                    "actual_type": token_data.type,
                    "token_id": redact_token_id(token_data.jti),
                },
            )

            raise ApplicationException(
                message="Invalid token type",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # Log successful token verification
        log_security_event(
            event_type="TOKEN_VERIFIED",
            message=f"{token_type.capitalize()} token verified successfully",
            level=SECURITY_AUDIT,
            user_id=token_data.sub,
            details={
                "token_id": redact_token_id(token_data.jti),
                "token_type": token_data.type,
                "expires_at": token_data.exp.isoformat() if token_data.exp else None,
            },
        )

        return token_data

    except ExpiredSignatureError:
        log_security_event(
            event_type="TOKEN_VERIFICATION_FAILED",
            message="Token has expired",
            level=SECURITY_AUDIT,
            details={"error": "expired_signature"},
        )

        raise ApplicationException(
            message="Token has expired",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    except JWTError as e:
        log_security_event(
            event_type="TOKEN_VERIFICATION_FAILED",
            message=f"Invalid token: {str(e)}",
            level=SECURITY_AUDIT,
            details={"error": str(e)},
        )

        raise ApplicationException(
            message="Invalid token",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
