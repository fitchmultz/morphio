from fastapi import APIRouter

from .login import router as login_router
from .registration import router as registration_router
from .token import router as token_router

# Create a combined router
router = APIRouter(tags=["Authentication"])

# Include all the sub-routers
router.include_router(login_router)
router.include_router(registration_router)
router.include_router(token_router)
