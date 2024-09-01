import operator
import typing

import sqlalchemy as sa
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from starlette_sqlalchemy.collection import Collection

T = typing.TypeVar("T")
_DT = typing.TypeVar("_DT")
_ChoiceLabelT = typing.TypeVar("_ChoiceLabelT")
_ChoiceValueT = typing.TypeVar("_ChoiceValueT")


class QueryError(Exception): ...


class NoResultError(QueryError, NoResultFound): ...


class MultipleResultsError(QueryError, MultipleResultsFound): ...


class Query:
    def __init__(self, dbsession: AsyncSession) -> None:
        self.dbsession = dbsession

    async def one(self, stmt: sa.Select[tuple[T]]) -> T:
        """Return exactly one row or raise an exception."""
        try:
            rows = await self.dbsession.scalars(stmt)
            return rows.one()
        except NoResultFound as ex:
            raise NoResultError from ex
        except MultipleResultsFound as ex:
            raise MultipleResultsError from ex

    async def one_or_none(self, stmt: sa.Select[tuple[T]]) -> T | None:
        """Return exactly one row or None.
        Note, if there are more than one row, it will raise MultipleResultsError exception.

        :param stmt: SQL statement
        :raises MultipleResultsError: if more than one row is found
        :return: T | None
        """
        try:
            rows = await self.dbsession.scalars(stmt)
            return rows.one_or_none()
        except MultipleResultsFound as ex:
            raise MultipleResultsError from ex

    async def one_or_raise(self, stmt: sa.Select[tuple[T]], exc: Exception) -> T:
        """Return exactly one row or raise a custom exception if no row exists."""
        entity = await self.one_or_none(stmt)
        if entity is None:
            raise exc
        return entity

    async def one_or_default(self, stmt: sa.Select[tuple[T]], default_value: _DT) -> T | _DT:
        entity = await self.one_or_none(stmt)
        return entity if entity else default_value

    async def all(self, stmt: sa.Select[tuple[T]]) -> Collection[T]:
        """Return all rows as a collection."""
        result = await self.dbsession.scalars(stmt)
        return Collection(result.all())

    async def iterator(self, stmt: sa.Select[tuple[T]], batch_size: int = 1000) -> typing.AsyncGenerator[T, None]:
        stmt = stmt.execution_options(yield_per=batch_size)
        result = await self.dbsession.stream(stmt)
        async for partition in result.partitions(batch_size):
            for row in partition:
                yield row[0]

    async def exists(self, stmt: sa.Select[tuple[T]]) -> bool:
        stmt = sa.select(sa.exists(stmt))
        result = await self.dbsession.scalars(stmt)
        return result.one() is True

    async def count(self, stmt: sa.Select[tuple[typing.Any]]) -> int:
        stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
        result = await self.dbsession.scalars(stmt)
        count = result.one()
        return int(count) if count else 0

    @typing.overload
    async def choices(
        self,
        stmt: sa.Select[tuple[T]],
        label_attr: str = "",
        value_attr: str = "",
    ) -> typing.AsyncGenerator[tuple[typing.Any, typing.Any], None]:  # pragma: no cover
        yield tuple(["", ""])  # type: ignore[misc]

    @typing.overload
    async def choices(
        self,
        stmt: sa.Select[tuple[T]],
        label_attr: typing.Callable[[T], _ChoiceLabelT],
        value_attr: typing.Callable[[T], _ChoiceValueT],
    ) -> typing.AsyncGenerator[tuple[_ChoiceValueT, _ChoiceLabelT], None]:  # pragma: no cover
        yield tuple(["", ""])  # type: ignore[misc]

    async def choices(
        self,
        stmt: sa.Select[tuple[T]],
        label_attr: typing.Any = str,
        value_attr: typing.Any = "id",
    ) -> typing.AsyncGenerator[tuple[_ChoiceValueT, _ChoiceLabelT], None]:
        label_getter: typing.Callable[[T], _ChoiceLabelT]
        value_getter: typing.Callable[[T], _ChoiceValueT]
        if isinstance(label_attr, str):
            label_getter = operator.attrgetter(label_attr)
        else:
            label_getter = label_attr

        if isinstance(value_attr, str):
            value_getter = operator.attrgetter(value_attr)
        else:
            value_getter = value_attr
        # label_getter = label_attr if callable(label_attr) else operator.attrgetter(label_attr)
        # value_getter = value_attr if callable(value_attr) else operator.attrgetter(value_attr)

        for item in await self.all(stmt):
            yield value_getter(item), label_getter(item)


query = Query
