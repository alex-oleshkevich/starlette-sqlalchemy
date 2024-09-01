import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from starlette_sqlalchemy.query import MultipleResultsError, NoResultError
from starlette_sqlalchemy.repos import Repo, RepoError, RepoFilter
from tests.models import User


class UserRepo(Repo[User]):
    model_class = User


@pytest.fixture
def user_repo(dbsession: AsyncSession) -> UserRepo:
    return UserRepo(dbsession)


def test_requires_model_class(dbsession: AsyncSession) -> None:
    class MissingModelRepo(Repo[User]):
        pass

    with pytest.raises(RepoError):
        MissingModelRepo(dbsession)


async def test_with_custom_base_query(dbsession: AsyncSession) -> None:
    class ModelRepo(Repo[User]):
        model_class = User
        base_query = sa.select(User).where(User.id > 8)

    repo = ModelRepo(dbsession)
    user = await repo.get_or_none(1)
    assert not user


class TestGet:
    async def test_get(self, user_repo: UserRepo) -> None:
        user = await user_repo.get(1)
        assert user.id == 1

    async def test_get_custom_pk(self, user_repo: UserRepo) -> None:
        user = await user_repo.get("02@user", pk_column="email")
        assert user.id == 2

    async def test_get_custom_pk_column(self, user_repo: UserRepo) -> None:
        user = await user_repo.get("02@user", pk_column=User.email)
        assert user.id == 2

    async def test_get_with_options(self, user_repo: UserRepo) -> None:
        user = await user_repo.get(2, options=[sa.orm.joinedload(User.profile)])
        assert user.profile.id == 2

    async def test_get_no_result(self, user_repo: UserRepo) -> None:
        with pytest.raises(NoResultError):
            await user_repo.get(-1)


class TestGetOrNone:
    async def test_get_or_none(self, user_repo: UserRepo) -> None:
        user = await user_repo.get_or_none(1)
        assert user is not None
        assert user.id == 1

        user = await user_repo.get_or_none(-1)
        assert user is None

    async def test_get_or_none_custom_pk(self, user_repo: UserRepo) -> None:
        user = await user_repo.get_or_none("02@user", pk_column="email")
        assert user is not None
        assert user.id == 2

    async def test_get_or_none_custom_pk_column(self, user_repo: UserRepo) -> None:
        user = await user_repo.get_or_none("02@user", pk_column=User.email)
        assert user is not None
        assert user.id == 2

    async def test_get_or_none_with_options(self, user_repo: UserRepo) -> None:
        user = await user_repo.get_or_none(2, options=[sa.orm.joinedload(User.profile)])
        assert user is not None
        assert user.id == 2
        assert user.profile is not None
        assert user.profile.id == 2


class ByEmail(RepoFilter[User]):
    def __init__(self, email: str) -> None:
        self.email = email

    def apply(self, stmt: sa.Select[tuple[User]]) -> sa.Select[tuple[User]]:
        return stmt.filter(User.email == self.email)


class ByNameLike(RepoFilter[User]):
    def __init__(self, name: str) -> None:
        self.name = name

    def apply(self, stmt: sa.Select[tuple[User]]) -> sa.Select[tuple[User]]:
        return stmt.filter(User.name.ilike(f"%{self.name}%"))


class TestAll:
    async def test_all(self, user_repo: UserRepo) -> None:
        users = await user_repo.all(ByEmail("02@user"))
        assert len(users) == 1
        user = users[0]
        assert user.id == 2

    async def test_all_no_filters(self, user_repo: UserRepo) -> None:
        users = await user_repo.all()
        assert len(users) == 9


class TestOne:
    async def test_one(self, user_repo: UserRepo) -> None:
        user = await user_repo.one(ByEmail("02@user"))
        assert user.id == 2

    async def test_no_rows(self, user_repo: UserRepo) -> None:
        with pytest.raises(NoResultError):
            await user_repo.one(ByEmail("-02@user"))

    async def test_multiple_rows(self, user_repo: UserRepo) -> None:
        with pytest.raises(MultipleResultsError):
            await user_repo.one(ByNameLike("user"))


class TestOneOrNone:
    async def test_one_or_none(self, user_repo: UserRepo) -> None:
        user = await user_repo.one_or_none(ByEmail("02@user"))
        assert user is not None
        assert user.id == 2

    async def test_no_rows(self, user_repo: UserRepo) -> None:
        user = await user_repo.one_or_none(ByEmail("-02@user"))
        assert user is None

    async def test_multiple_rows(self, user_repo: UserRepo) -> None:
        with pytest.raises(MultipleResultsError):
            await user_repo.one_or_none(ByNameLike("user"))


class TestOneOrDefault:
    async def test_one_or_default(self, user_repo: UserRepo) -> None:
        user = await user_repo.one_or_default(ByEmail("02@user"), default=User(id=0))
        assert user.id == 2

    async def test_no_rows(self, user_repo: UserRepo) -> None:
        user = await user_repo.one_or_default(ByEmail("-02@user"), default=User(id=0))
        assert user.id == 0

    async def test_multiple_rows(self, user_repo: UserRepo) -> None:
        with pytest.raises(MultipleResultsError):
            await user_repo.one_or_default(ByNameLike("user"), default=User(id=0))


class TestOneOrRaise:
    async def test_one_or_raise(self, user_repo: UserRepo) -> None:
        user = await user_repo.one_or_raise(ByEmail("02@user"), ValueError("User not found"))
        assert user.id == 2

    async def test_no_rows(self, user_repo: UserRepo) -> None:
        with pytest.raises(ValueError, match="User not found"):
            await user_repo.one_or_raise(ByEmail("-02@user"), ValueError("User not found"))

    async def test_multiple_rows(self, user_repo: UserRepo) -> None:
        with pytest.raises(MultipleResultsError):
            await user_repo.one_or_raise(ByNameLike("user"), ValueError("User not found"))
