import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...models.user import User
from ...schemas.auth_schema import (
    AuthTokenPayload,
    ChangePasswordRequest,
    Token,
    UserCreate,
    UserOut,
)
from ...schemas.response_schema import ApiResponse
from ...services.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    is_password_complex,
    set_refresh_cookie,
    verify_password,
)
from ...utils.decorators import rate_limit
from ...utils.error_handlers import ApplicationException
from ...utils.response_utils import ResponseStatus, create_response
from ...utils.route_helpers import common_responses, handle_route_errors

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/register",
    operation_id="register",
    response_model=ApiResponse[AuthTokenPayload],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "User registered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "User registered successfully",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh_token": "",
                            "user": {
                                "id": 1,
                                "email": "some@example.com",
                                "display_name": "NewUser",
                                "role": "USER",
                                "created_at": "2025-01-01T12:00:00Z",
                                "last_login": None,
                                "is_active": True,
                                "content_count": 0,
                            },
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Email already registered",
                        "data": {"error_type": "ApplicationException", "details": {}},
                    }
                }
            },
        },
        403: {
            "description": "Registration disabled",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Registration is currently disabled",
                        "data": {"error_type": "ApplicationException", "details": {}},
                    }
                }
            },
        },
        **common_responses,
    },
)
@rate_limit("60/minute")
@handle_route_errors
async def register(
    request: Request,
    response: Response,
    user: UserCreate = Body(
        ...,
        examples=[
            {
                "email": "some@example.com",
                "password": "Str0ngP@ssword!",
                "display_name": "NewUser",
            }
        ],
    ),
    db: AsyncSession = Depends(get_db),
):
    if not settings.REGISTRATION_ENABLED:
        raise ApplicationException(
            message="Registration is currently disabled",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    logger.debug(f"Attempting to register user with email: {user.email}")
    existing_user = await db.scalar(select(User).where(User.email == user.email))
    if existing_user:
        logger.warning(f"Registration attempt with existing email: {user.email}")
        raise ApplicationException(
            message="Email already registered",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Password complexity is already validated by schema, but check explicitly for extra safety
    is_password_complex(user.password)

    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        hashed_password=hashed_password,
        display_name=user.display_name,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(data={"sub": str(new_user.id)})

    # Create a refresh token and set it in a cookie
    refresh_token_data = create_refresh_token(data={"sub": str(new_user.id)})

    # Set refresh token in secure HTTP-only cookie
    set_refresh_cookie(response, refresh_token_data)

    response_data = Token(
        access_token=access_token,
        refresh_token="",  # We don't return it in the JSON, left empty for schema
        user=UserOut.model_validate(new_user),
    )

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="User registered successfully",
        data=response_data.model_dump(),
    )


@router.post(
    "/change-password",
    operation_id="change_password",
    response_model=ApiResponse[None],
    responses={
        200: {
            "description": "Password Changed Successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Password updated successfully.",
                        "data": None,
                    }
                }
            },
        },
        400: {
            "description": "Bad Request",
            "content": {"application/json": {"example": {"detail": "Incorrect current password"}}},
        },
        **common_responses,
    },
)
@rate_limit("60/minute")
@handle_route_errors
async def change_password(
    request: ChangePasswordRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )

    # Validate password complexity (raises ApplicationException on failure)
    is_password_complex(request.new_password)

    current_user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    logger.info(f"Password changed for user: {current_user.email}")
    return create_response(
        message="Password updated successfully.",
        status=ResponseStatus.SUCCESS,
    )
