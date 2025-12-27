import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.user import User
from ...schemas.auth_schema import AuthTokenPayload, Token, UserLogin, UserOut
from ...schemas.response_schema import ApiResponse
from ...services.redis import add_to_token_blacklist
from ...services.security import (
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    get_current_user,
    set_refresh_cookie,
    verify_password,
    verify_token,
)
from ...utils.decorators import rate_limit
from ...utils.response_utils import ResponseStatus, create_response, utc_now
from ...utils.route_helpers import common_responses, handle_route_errors
from ...utils.security_logger import (
    SECURITY_AUDIT,
    SecurityEventType,
    audit,
    log_security_event,
    redact_token_id,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
logger = logging.getLogger(__name__)


@router.post(
    "/login",
    operation_id="login",
    response_model=ApiResponse[AuthTokenPayload],
    responses={
        200: {
            "description": "Successful Login",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "xxx",
                        "user": {
                            "id": 1,
                            "email": "user1@example.com",
                            "display_name": "user1",
                        },
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized",
            "content": {"application/json": {"example": {"detail": "Incorrect email or password"}}},
        },
        **common_responses,
    },
)
@rate_limit("60/minute")
@handle_route_errors
@audit(SecurityEventType.LOGIN_ATTEMPT, "Login attempt for user: {user_login.email}")
async def login(
    request: Request,
    response: Response,
    user_login: UserLogin = Body(...),
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Attempting login for user: {user_login.email}")
    user = await db.scalar(select(User).where(User.email == user_login.email))
    if not user:
        logger.warning(f"Login attempt for non-existent user: {user_login.email}")
        log_security_event(
            event_type=SecurityEventType.LOGIN_FAILURE,
            message=f"Login attempt for non-existent user: {user_login.email}",
            level=SECURITY_AUDIT,
            details={"email": user_login.email, "reason": "user_not_found"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Ensure user is active
    if not user.is_active:
        log_security_event(
            event_type=SecurityEventType.LOGIN_FAILURE,
            message=f"Login attempt for inactive account: {user_login.email}",
            level=SECURITY_AUDIT,
            user_id=user.id,
            details={"email": user_login.email, "reason": "account_inactive"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    if not verify_password(user_login.password, user.hashed_password):
        logger.warning(f"Login attempt with incorrect password for user: {user_login.email}")
        log_security_event(
            event_type=SecurityEventType.LOGIN_FAILURE,
            message=f"Login attempt with incorrect password: {user_login.email}",
            level=SECURITY_AUDIT,
            user_id=user.id,
            details={"email": user_login.email, "reason": "incorrect_password"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Create a token family and JWT ID for tracking and rotation
    token_family = secrets.token_hex(8)
    token_id = secrets.token_hex(16)

    # Include token family and ID in the tokens
    token_data = {"sub": str(user.id), "jti": token_id, "family": token_family}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    setattr(user, "last_login", utc_now())
    await db.commit()

    # Set refresh token in secure HTTP-only cookie
    set_refresh_cookie(response, refresh_token)

    logger.info(f"User logged in: {user.email}")

    # Log successful login
    log_security_event(
        event_type=SecurityEventType.LOGIN_SUCCESS,
        message=f"User logged in successfully: {user.email}",
        level=SECURITY_AUDIT,
        user_id=user.id,
        details={
            "email": user.email,
            "token_id": token_id,
            "token_family": token_family,
        },
    )

    token_data = Token(
        access_token=access_token,
        refresh_token="",  # no longer returning refresh token in JSON
        user=UserOut.model_validate(user),
    )
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Login successful",
        data=token_data.model_dump(),
    )


@router.post(
    "/logout",
    operation_id="logout",
    response_model=ApiResponse[None],
    responses={
        200: {
            "description": "Successfully Logged Out",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Logged out successfully.",
                        "data": None,
                    }
                }
            },
        },
        **common_responses,
    },
)
@rate_limit("60/minute")
@handle_route_errors
async def logout(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    response: Response,
):
    # Revoke refresh token if present (blacklist it)
    refresh_token_cookie = request.cookies.get("refresh_token")
    if refresh_token_cookie:
        try:
            token_payload = verify_token(refresh_token_cookie, token_type="refresh")
            if token_payload.jti:
                # Calculate remaining TTL
                exp_timestamp = token_payload.exp.timestamp() if token_payload.exp else 0
                ttl = int(exp_timestamp - utc_now().timestamp())
                if ttl > 0:
                    await add_to_token_blacklist(token_payload.jti, ttl)
                    logger.debug(
                        f"Token {redact_token_id(token_payload.jti)} blacklisted on logout"
                    )
        except Exception as e:
            # Token may be invalid/expired, but still clear the cookie
            logger.debug(f"Could not revoke refresh token on logout: {e}")

    # Clear all auth cookies with consistent attributes
    clear_auth_cookies(response)

    logger.info(f"User logged out: {current_user.email}")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Logged out successfully.",
        status_code=status.HTTP_200_OK,
    )
