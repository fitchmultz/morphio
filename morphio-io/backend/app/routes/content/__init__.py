"""Content routes - aggregated from submodules."""

from fastapi import APIRouter

from .comments import router as comments_router
from .conversations import router as conversations_router
from .crud import router as crud_router

# Create a combined router
router = APIRouter(tags=["Content"])

# Include all the sub-routers
router.include_router(crud_router)
router.include_router(comments_router)
router.include_router(conversations_router)
