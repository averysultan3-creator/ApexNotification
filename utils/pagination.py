from dataclasses import dataclass
from typing import TypeVar, Generic, List, Tuple

T = TypeVar("T")


@dataclass
class PageResult(Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 1
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @property
    def has_prev(self) -> bool:
        return self.page > 0

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages - 1


def paginate(items: List[T], total: int, page: int, page_size: int) -> PageResult[T]:
    return PageResult(items=items, total=total, page=page, page_size=page_size)
