import abc
import contextlib
import math
import typing

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from starlette_sqlalchemy.query import query

T = typing.TypeVar("T")


def get_page_value(request: Request, param_name: str = "page") -> int:
    page = 1
    with contextlib.suppress(TypeError, ValueError):
        page = max(1, int(request.query_params.get(param_name, 1)))
    return page


def get_page_size_value(
    request: Request,
    param_name: str = "page_size",
    max_page_size: int = 100,
    default: int = 20,
) -> int:
    try:
        page_size = int(request.query_params.get(param_name, default))
        return min(page_size, max_page_size)
    except (TypeError, ValueError):
        return default


class BaseStyle(abc.ABC):  # pragma: no cover
    @abc.abstractmethod
    def iterate_pages(self, current_page: int, total_pages: int) -> typing.Iterator[int | None]:
        raise NotImplementedError


class SlidingStyle(BaseStyle):
    def __init__(
        self,
        before_current: int = 3,
        after_current: int = 3,
    ) -> None:
        self.before_current = before_current
        self.after_current = after_current

    def iterate_pages(self, current_page: int, total_pages: int) -> typing.Iterator[int | None]:
        if total_pages <= 1:
            return

        # determine left boundary
        left = max(1, current_page - self.before_current)
        for page in range(left, min(current_page, total_pages)):
            yield page

        yield current_page

        # determine right boundary
        right = min(total_pages, current_page + self.after_current)
        for page in range(current_page + 1, right + 1):
            yield page


class Page(typing.Generic[T]):
    def __init__(
        self, items: typing.Sequence[T], total: int, page: int, page_size: int, style: BaseStyle | None = None
    ) -> None:
        self.rows = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self._style = style or SlidingStyle()
        self._pointer = 0

    @property
    def total_pages(self) -> int:
        """Total pages in the row set."""
        return math.ceil(self.total / self.page_size)

    @property
    def has_next(self) -> bool:
        """Test if the next page is available."""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Test if the previous page is available."""
        return self.page > 1

    @property
    def has_other(self) -> bool:
        """Test if page has next or previous pages."""
        return self.has_next or self.has_previous

    @property
    def next_page(self) -> int:
        """
        Next page number.

        Always returns an integer. If there is no more pages the current page number returned.
        """
        return min(self.total_pages, self.page + 1)

    @property
    def previous_page(self) -> int:
        """
        Previous page number.

        Always returns an integer. If there is no previous page, the number 1 returned.
        """
        return max(1, self.page - 1)

    @property
    def start_index(self) -> int:
        """The 1-based index of the first item on this page."""
        if self.page == 1:
            return 1
        return (self.page - 1) * self.page_size + 1

    @property
    def end_index(self) -> int:
        """The 1-based index of the last item on this page."""
        return min(self.start_index + self.page_size - 1, self.total)

    def iter_pages(self) -> typing.Generator[int | None, None, None]:
        """Iterate over the page numbers in the pagination.
        If the page number is None, it represents an ellipsis.
        """
        yield from self._style.iterate_pages(self.page, self.total_pages)

    def __iter__(self) -> typing.Iterator[T]:
        return iter(self.rows)

    def __next__(self) -> T:
        if self._pointer == len(self.rows):
            raise StopIteration
        self._pointer += 1
        return self.rows[self._pointer - 1]

    def __getitem__(self, item: int) -> T:
        return self.rows[item]

    def __len__(self) -> int:
        return len(self.rows)

    def __bool__(self) -> bool:
        return len(self.rows) > 0

    def __str__(self) -> str:
        return f"Page {self.page} of {self.total_pages}, rows {self.start_index} - {self.end_index} of {self.total}."

    def __repr__(self) -> str:
        return f"<Page: page={self.page}, total_pages={self.total_pages}>"


def _safe_int(value: str | int, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


class Paginator(abc.ABC):
    def __init__(self, dbsession: AsyncSession) -> None:
        self.dbsession = dbsession


class PageNumberPaginator(Paginator):
    async def paginate(
        self, stmt: sa.Select[tuple[T]], page: int, page_size: int, style: BaseStyle | None = None
    ) -> Page[T]:
        offset = (page - 1) * page_size
        total_rows = await self.count(stmt)

        stmt = stmt.limit(page_size).offset(offset)
        rows = await query(self.dbsession).all(stmt)

        return Page(total=total_rows, items=list(rows), page=page, page_size=page_size, style=style)

    async def count(self, stmt: sa.Select[tuple[T]]) -> int:
        return await query(self.dbsession).count(stmt)

    async def paginate_from_request(
        self,
        request: Request,
        stmt: sa.Select[tuple[T]],
        page_size: int = 100,
        page_param: str = "page",
        page_size_param: str = "page_size",
        max_page_size: int = 100,
    ) -> Page[T]:
        current_page = _safe_int(request.query_params.get(page_param, 1), 1)
        current_page = max(1, current_page)

        limit = _safe_int(request.query_params.get(page_size_param, 0), page_size)
        limit = min(max_page_size, limit)
        return await self.paginate(stmt, current_page, limit)
