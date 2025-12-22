from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataclasses import dataclass

T = TypeVar("T")


@dataclass
class PageResult(Generic[T]):
    items: list[T]
    total: int


class PaginatedQuery(Generic[T]):
    def __init__(
        self,
        model: Type[T],
        filters: List = [],
        order_by: Optional[Any] = None,
        options: List[Any] = [],
    ):
        self.model = model
        self.filters = filters
        self.order_by = order_by
        self.options = options

    async def execute(self, db: AsyncSession, page: int, per_page: int) -> PageResult[T]:
        query = select(self.model).where(*self.filters)
        if self.order_by is not None:
            query = query.order_by(self.order_by)
        if self.options:
            query = query.options(*self.options)

        total = await db.scalar(select(func.count()).select_from(query.subquery()))
        results = await db.execute(query.offset((page - 1) * per_page).limit(per_page))
        items = results.unique().scalars().all()

        return PageResult[T](items=list(items), total=int(total or 0))
