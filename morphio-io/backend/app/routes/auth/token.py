import logging
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response, status

from ...dependencies import DbSession
from ...models.user import User
from ...schemas.auth_schema import AuthTokenPayload, CsrfTokenPayload, Token, UserOut
from ...schemas.response_schema import ApiResponse
from ...services.redis import add_to_token_blacklist, is_token_blacklisted
from ...services.security import (
    clear_refresh_cookie,
    create_access_token,
    create_refresh_token,
    set_csrf_cookie,
    set_refresh_cookie,
    verify_token,
)
from ...utils.error_handlers import ApplicationException
from ...utils.decorators import rate_limit
from ...utils.response_utils import ResponseStatus, create_response, utc_now
from ...utils.route_helpers import common_responses, handle_route_errors
from ...utils.security_logger import redact_token_id

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/refresh-token",
    operation_id="refresh_token",
    response_model=ApiResponse[AuthTokenPayload],
    responses={
        **common_responses,
        200: {
            "description": "Refresh token rotated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Refresh token updated",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh_token": "",
                            "user": {
                                "id": 1,
                                "email": "user1@example.com",
                                "display_name": "user1",
                                "role": "USER",
                                "created_at": "2025-01-01T12:00:00Z",
                                "last_login": "2025-01-10T08:30:00Z",
                                "is_active": True,
                                "content_count": 3,
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Invalid refresh token",
                        "data": {"error_type": "HTTPException", "details": {}},
                    }
                }
            },
        },
    },
    openapi_extra={
        "parameters": [
            {
                "name": "refresh_token",
                "in": "cookie",
                "required": True,
                "schema": {"type": "string"},
                "example": "refresh_token_cookie_value",
            }
        ]
    },
)
@rate_limit("30/minute")
@handle_route_errors
async def refresh_token(
    request: Request,
    response: Response,
    db: DbSession,
):
    # Retrieve refresh token from secure cookie
    refresh_token_cookie: Optional[str] = request.cookies.get("refresh_token")
    if not refresh_token_cookie:
        raise HTTPException(status_code=401, detail="No refresh token cookie")

    try:
        # Use verify_token to ensure this is actually a refresh token (not access token)
        token_payload = verify_token(refresh_token_cookie, token_type="refresh")
    except ApplicationException as e:
        logger.warning(f"Invalid refresh token: {e.message}")
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail=e.message)
    except Exception as e:
        logger.error(f"Invalid refresh token in cookie: {str(e)}")
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id: str = token_payload.sub
    token_id: str = token_payload.jti or ""
    token_family: str = token_payload.family or ""

    # Require jti and family for refresh tokens (security requirement)
    if not token_id or not token_family:
        logger.warning("Refresh token missing required fields (jti or family)")
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Invalid refresh token format")

    if not user_id:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Check if this token has been blacklisted
    if token_id and await is_token_blacklisted(token_id):
        logger.warning(f"Attempt to use blacklisted token: {redact_token_id(token_id)}")
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
        )

    user = await db.get(User, int(user_id))
    if user is None:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure user is active
    if not user.is_active:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Add the current token to the blacklist (one-time use)
    if token_id:
        # Calculate token expiry - we'll keep it in the blacklist until it would have expired
        exp_timestamp = token_payload.exp.timestamp() if token_payload.exp else 0
        expiry = int(exp_timestamp - utc_now().timestamp())
        if expiry > 0:
            await add_to_token_blacklist(token_id, expiry)
            logger.debug(f"Token {redact_token_id(token_id)} blacklisted for {expiry} seconds")

    # Generate a new JWT ID for tracking
    new_token_id = secrets.token_hex(16)

    # Create tokens with the family and ID info
    token_data = {"sub": str(user.id), "jti": new_token_id, "family": token_family}
    new_access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)

    # Update cookie with new refresh token
    set_refresh_cookie(response, new_refresh_token)

    token_data = Token(
        access_token=new_access_token,
        refresh_token="",  # Not returned in body
        user=UserOut.model_validate(user),
    )
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Refresh token updated",
        data=token_data.model_dump(),
    )


@router.get(
    "/csrf-token",
    operation_id="get_csrf_token",
    response_model=ApiResponse[CsrfTokenPayload],
    responses={
        200: {
            "description": "CSRF Token",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "CSRF token generated",
                        "data": {"csrf_token": "abc123"},
                    }
                }
            },
        },
        **common_responses,
    },
)
@rate_limit("60/minute")
@handle_route_errors
async def get_csrf_token(request: Request, response: Response):
    """
    Generate a CSRF token and set it in a cookie.
    Returns the token in the response body for AJAX requests.
    """
    # Generate a secure random token
    token = secrets.token_hex(32)

    # Set the token in a cookie using consistent helper
    set_csrf_cookie(response, token)

    logger.debug("CSRF token generated")

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="CSRF token generated",
        data={"csrf_token": token},
    )
