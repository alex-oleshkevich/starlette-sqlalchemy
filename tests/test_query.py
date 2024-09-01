import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from starlette_sqlalchemy.query import MultipleResultsError, NoResultError, query
from tests.models import User


class TestOne:
    async def test_one(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).where(User.id == 1)
        model = await query(dbsession).one(stmt)
        assert model.id == 1

    async def test_one_no_rows(self, dbsession: AsyncSession) -> None:
        with pytest.raises(NoResultError):
            stmt = sa.select(User).where(User.id == -1)
            await query(dbsession).one(stmt)

    async def test_one_multiple_rows(self, dbsession: AsyncSession) -> None:
        with pytest.raises(MultipleResultsError):
            stmt = sa.select(User).where(sa.or_(User.id == 1, User.id == 2))
            await query(dbsession).one(stmt)


class TestOneOrNone:
    async def test_one_or_none(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).where(User.id == 1)
        model = await query(dbsession).one_or_none(stmt)
        assert model is not None
        assert model.id == 1

    async def test_one_or_none_no_row(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).where(User.id == -1)
        model = await query(dbsession).one_or_none(stmt)
        assert model is None

    async def test_one_or_none_multiple_rows(self, dbsession: AsyncSession) -> None:
        with pytest.raises(MultipleResultsError):
            stmt = sa.select(User).where(sa.or_(User.id == 1, User.id == 2))
            await query(dbsession).one_or_none(stmt)


class TestOneOrDefault:
    async def test_one_or_default(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).where(User.id == 1)
        model = await query(dbsession).one_or_default(stmt, User(id=-1, name="n/a", email="n/a"))
        assert model.id == 1

    async def test_one_or_default_no_row(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).where(User.id == -1)
        model = await query(dbsession).one_or_default(stmt, User(id=-1, name="n/a", email="n/a"))
        assert model.id == -1


async def test_all(dbsession: AsyncSession) -> None:
    stmt = sa.select(User)
    models = await query(dbsession).all(stmt)
    assert len(models) == 9


async def test_iterator(dbsession: AsyncSession) -> None:
    stmt = sa.select(User).limit(3)
    iterator = query(dbsession).iterator(stmt, batch_size=1)
    assert [1, 2, 3] == [model.id async for model in iterator]


async def test_exists(dbsession: AsyncSession) -> None:
    stmt = sa.select(User).where(User.id == 1)
    assert await query(dbsession).exists(stmt) is True

    stmt = sa.select(User).where(User.id == -1)
    assert await query(dbsession).exists(stmt) is False


async def test_count(dbsession: AsyncSession) -> None:
    stmt = sa.select(User)
    assert await query(dbsession).count(stmt) == 9

    stmt = sa.select(User).where(User.id == 1)
    assert await query(dbsession).count(stmt) == 1


class TestChoices:
    async def test_choices(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).limit(3)
        choices = [choice async for choice in query(dbsession).choices(stmt)]
        assert choices == [(1, "user_01"), (2, "user_02"), (3, "user_03")]

    async def test_choices_string_keys(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).limit(3)
        choices: list[tuple[int, str]] = [
            choice async for choice in query(dbsession).choices(stmt, label_attr="name", value_attr="id")
        ]
        assert choices == [(1, "user_01"), (2, "user_02"), (3, "user_03")]

    async def test_choices_callable_keys(self, dbsession: AsyncSession) -> None:
        stmt = sa.select(User).limit(3)
        choices = [
            choice
            async for choice in query(dbsession).choices(
                stmt, label_attr=lambda obj: obj.name, value_attr=lambda o: o.id
            )
        ]
        assert choices == [(1, "user_01"), (2, "user_02"), (3, "user_03")]
