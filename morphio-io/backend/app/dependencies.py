"""Purpose: Centralize reusable FastAPI dependency aliases.
Responsibilities: Provide typed aliases for common dependency injection patterns.
Scope: Shared backend route and service signatures that depend on auth or database access.
Usage: Import `CurrentUser` and `DbSession` instead of repeating `Depends(...)` annotations.
Invariants/Assumptions: Aliases resolve to the canonical auth and database dependency providers.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models.user import User
from .services.security import get_current_user

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
