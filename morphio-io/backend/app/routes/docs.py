from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict

from ..models.user import User
from ..services.security import get_current_user

router = APIRouter()


class Item(BaseModel):
    name: str
    price: float

    model_config = ConfigDict(json_schema_extra={"env": "item"})


@router.post("/items/", response_model=Item)
async def create_item(item: Item):
    """
    Create a new item.

    - **name**: The name of the item.
    - **price**: The price of the item.
    """
    return item


@router.get("/items/{item_id}")
async def read_item(
    item_id: int = Path(..., title="The ID of the item to get", ge=1),
    q: str | None = Query(None, max_length=50),
):
    """
    Retrieve an item by its ID.

    - **item_id**: The ID of the item. Must be 1 or greater.
    - **q**: Optional query string for searching. Max 50 characters.
    """
    return {"item_id": item_id, "q": q}


@router.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get info about the current authenticated user.
    """
    return current_user
