from __future__ import annotations

import abc
import typing

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.base import ExecutableOption

from starlette_sqlalchemy.collection import Collection
from starlette_sqlalchemy.query import NoResultError, query

T = typing.TypeVar("T")


class RepoError(Exception):
    """Base class for exceptions in this module."""


class RepoFilter(typing.Generic[T], abc.ABC):
    @abc.abstractmethod
    def apply(self, stmt: sa.Select[tuple[T]]) -> sa.Select[tuple[T]]:  # pragma: no cover
        raise NotImplementedError()

    def __and__(self, other: RepoFilter[T]) -> RepoFilter[T]:
        return CompositeFilter(self, other)


class CompositeFilter(RepoFilter[T]):
    def __init__(self, left: RepoFilter[T], right: RepoFilter[T]) -> None:
        self.left = left
        self.right = right

    def apply(self, stmt: sa.Select[tuple[T]]) -> sa.Select[tuple[T]]:
        stmt = self.left.apply(stmt)
        return self.right.apply(stmt)


class Repo(typing.Generic[T]):
    model_class: type[T] | None = None
    base_query: sa.Select[tuple[T]] | None = None

    def __init__(self, dbsession: AsyncSession) -> None:
        self.dbsession = dbsession
        self.query = query(dbsession)
        if self.model_class is None:
            raise RepoError("No model class defined for repo '{name}'".format(name=self.__class__.__name__))
        if self.base_query is None:
            self.base_query = sa.select(self.model_class)

    def get_base_query(self) -> sa.Select[tuple[T]]:
        """Return the base query for this repo."""
        assert self.base_query is not None
        return self.base_query

    async def get(
        self,
        pk: typing.Any,
        pk_column: str | InstrumentedAttribute[typing.Any] = "id",
        options: typing.Sequence[ExecutableOption] | None = None,
    ) -> T:
        """Get exactly one row by primary key.

        If the row does not exist, raise a `NoResultError` exception.
        If more than one row exists, raise a `MultipleResultsError` exception.

        :raises NoResultError: if no row is found
        :raises MultipleResultsError: if more than one row is found
        """
        stmt = self.get_base_query()
        column: InstrumentedAttribute[typing.Any]
        if isinstance(pk_column, str):
            column = getattr(self.model_class, pk_column)
        else:
            column = pk_column

        if options:
            stmt = stmt.options(*options)

        stmt = stmt.where(column == pk)
        return await self.query.one(stmt)

    async def get_or_none(
        self,
        pk: typing.Any,
        pk_column: str | InstrumentedAttribute[typing.Any] = "id",
        options: typing.Sequence[ExecutableOption] | None = None,
    ) -> T | None:
        """Get exactly one row by primary key, or None if row does not exist.

        If more than one row exists, raise a `MultipleResultsError` exception.

        :raises MultipleResultsError: if more than one row is found
        """
        try:
            return await self.get(pk, pk_column, options)
        except NoResultError:
            return None

    def get_filtered_query(self, filter_: RepoFilter[T]) -> sa.Select[tuple[T]]:
        """Return a query with the given filters applied."""
        stmt = self.get_base_query()
        return filter_.apply(stmt)

    async def one(self, filter_: RepoFilter[T]) -> T:
        """Return exactly one row that matches the given filters.

        If no row exists, raise a `NoResultError` exception.
        If more than one row exists, raise a `MultipleResultsError` exception.

        :raises NoResultError: if no row is found
        :raises MultipleResultsError: if more than one row is found
        """

        stmt = self.get_filtered_query(filter_)
        return await self.query.one(stmt)

    async def one_or_none(self, filter_: RepoFilter[T]) -> T | None:
        """Return exactly one row that matches the given filters, or None if no row exists.

        If more than one row exists, raise a `MultipleResultsError` exception.

        :raises MultipleResultsError: if more than one row is found
        """

        stmt = self.get_filtered_query(filter_)
        return await self.query.one_or_none(stmt)  # type: ignore[arg-type]

    async def one_or_default(self, filter_: RepoFilter[T], default: T) -> T:
        """Return all rows that match the given filters."""

        stmt = self.get_filtered_query(filter_)
        return await self.query.one_or_default(stmt, default)

    async def one_or_raise(self, filter_: RepoFilter[T], exc: Exception) -> T | typing.NoReturn:
        """Return all rows that match the given filters."""

        stmt = self.get_filtered_query(filter_)
        return await self.query.one_or_raise(stmt, exc)

    async def all(self, filter_: RepoFilter[T] | None = None) -> Collection[T]:
        """Return all rows that match the given filters."""

        if filter_ is None:
            stmt = self.get_base_query()
        else:
            stmt = self.get_filtered_query(filter_)
        return await self.query.all(stmt)
