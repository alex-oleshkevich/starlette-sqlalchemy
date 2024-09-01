import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from starlette_sqlalchemy.pagination import get_page_size_value, get_page_value, Page, PageNumberPaginator, SlidingStyle
from tests.models import User


class TestPage:
    def test_page(self) -> None:
        rows = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        page = Page(rows, total=101, page=2, page_size=10)
        assert page.total_pages == 11
        assert page.has_next
        assert page.has_previous
        assert page.has_other
        assert page.previous_page == 1
        assert page.next_page == 3
        assert page.start_index == 11
        assert page.end_index == 20
        assert len(page) == 10

        assert bool(page)
        assert page[0] == 1

        with pytest.raises(IndexError):
            assert rows[11]

    def test_page_iterator(self) -> None:
        rows = [1, 2]
        page = Page(rows, total=2, page=1, page_size=2)
        assert rows == [p for p in page]
        assert next(page) == 1
        assert next(page) == 2

        with pytest.raises(StopIteration):
            assert next(page) == 3

    def test_page_no_other_pages(self) -> None:
        page: Page[int] = Page([], total=2, page=1, page_size=2)
        assert not page.has_other

    def test_stops_iteration_when_all_left_controls_equal_page_count(self) -> None:
        page: Page[int] = Page([], total=4, page=1, page_size=2)
        with pytest.raises(StopIteration):
            iterator = page.iter_pages()
            assert [x for x in iterator] == [1, 2]
            assert next(iterator)

    def test_iterator_without_pages(self) -> None:
        page: Page[int] = Page([], total=0, page=1, page_size=1)
        with pytest.raises(StopIteration):
            assert next(page.iter_pages())

    def test_page_start_index_for_first_page(self) -> None:
        rows = [1, 2]
        page = Page(rows, total=2, page=1, page_size=2)
        assert page.start_index == 1
        assert page.end_index == 2

    def test_page_next_prev_pages(self) -> None:
        rows = [1, 2]
        page = Page(rows, total=1, page=1, page_size=1)
        assert page.has_next is False
        assert page.has_previous is False
        assert page.next_page == 1
        assert page.previous_page == 1

    def test_iter_pages(self) -> None:
        page = Page([x for x in range(200)], total=200, page_size=10, page=1, style=SlidingStyle())
        assert list(page.iter_pages()) == [1, 2, 3, 4]

    def test_page_repr(self) -> None:
        rows = [1, 2]
        page = Page(rows, total=2, page=1, page_size=2)
        assert repr(page) == "<Page: page=1, total_pages=1>"

    def test_page_str(self) -> None:
        rows = [1, 2]
        page = Page(rows, total=2, page=1, page_size=2)
        assert str(page) == "Page 1 of 1, rows 1 - 2 of 2."


class TestSlidingPaginationStyle:
    def test_current_in_the_middle(self) -> None:
        style = SlidingStyle(
            before_current=3,
            after_current=3,
        )
        pages = list(style.iterate_pages(5, 10))
        assert pages == [2, 3, 4, 5, 6, 7, 8]

    def test_current_is_first(self) -> None:
        style = SlidingStyle(before_current=3, after_current=3)
        pages = list(style.iterate_pages(1, 10))
        assert pages == [1, 2, 3, 4]

    def test_current_is_last(self) -> None:
        style = SlidingStyle(before_current=3, after_current=3)
        pages = list(style.iterate_pages(10, 10))
        assert pages == [7, 8, 9, 10]

    def test_current_middle_of_left_edge(self) -> None:
        style = SlidingStyle(before_current=3, after_current=3)
        pages = list(style.iterate_pages(3, 10))
        assert pages == [1, 2, 3, 4, 5, 6]

    def test_current_middle_of_right_edge(self) -> None:
        style = SlidingStyle(before_current=3, after_current=3)
        pages = list(style.iterate_pages(7, 10))
        assert pages == [4, 5, 6, 7, 8, 9, 10]


def test_get_page_value() -> None:
    assert get_page_value(Request({"query_string": b"", "type": "http"})) == 1
    assert get_page_value(Request({"query_string": b"page=1", "type": "http"})) == 1
    assert get_page_value(Request({"query_string": b"page=text", "type": "http"})) == 1
    assert get_page_value(Request({"query_string": b"current_page=1", "type": "http"}), param_name="current_page") == 1


def test_get_page_size_value() -> None:
    assert get_page_size_value(Request({"query_string": b"", "type": "http"}), default=2) == 2
    assert get_page_size_value(Request({"query_string": b"page_size=20", "type": "http"})) == 20
    assert get_page_size_value(Request({"query_string": b"size=20", "type": "http"}), param_name="size") == 20
    assert get_page_size_value(Request({"query_string": b"page_size=100", "type": "http"}), max_page_size=50) == 50
    assert get_page_size_value(Request({"query_string": b"page_size=text", "type": "http"}), default=2) == 2


class TestPageNumberPaginator:
    async def test_paginates(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).order_by(User.id)
        paginator = PageNumberPaginator(dbsession)
        page = await paginator.paginate(stmt, page=1, page_size=2)
        assert page.total_pages == 5

    async def test_paginates_from_request_object(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).order_by(User.id)
        paginator = PageNumberPaginator(dbsession)

        request = Request(
            scope={
                "type": "http",
                "query_string": b"page=1&page_size=2",
            }
        )
        page = await paginator.paginate_from_request(request, stmt, page_size=2)
        assert page.total_pages == 5

    async def test_custom_page_param(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).order_by(User.id)
        paginator = PageNumberPaginator(dbsession)

        request = Request(
            scope={
                "type": "http",
                "query_string": b"pg=1&page_size=2",
            }
        )
        page = await paginator.paginate_from_request(request, stmt, page_size=2, page_param="pg")
        assert page.total_pages == 5

    async def test_custom_page_size_param(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).order_by(User.id)
        paginator = PageNumberPaginator(dbsession)

        request = Request(
            scope={
                "type": "http",
                "query_string": b"page&ps=2",
            }
        )
        page = await paginator.paginate_from_request(request, stmt, page_size=2, page_size_param="ps")
        assert page.total_pages == 5

    async def test_max_page_size(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).order_by(User.id)
        paginator = PageNumberPaginator(dbsession)

        request = Request(
            scope={
                "type": "http",
                "query_string": b"page&page_size=200",
            }
        )
        page = await paginator.paginate_from_request(request, stmt, page_size=2, max_page_size=2)
        assert page.total_pages == 5
