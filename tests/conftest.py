import typing

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncEngine, AsyncSession, create_async_engine

from tests.models import Base, Profile, User

AsyncSessionMaker = async_sessionmaker[AsyncSession]


@pytest.fixture(scope="session")
async def dbengine() -> typing.AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        yield engine


@pytest.fixture()
def dbsession_maker(dbengine: AsyncEngine) -> AsyncSessionMaker:
    return async_sessionmaker(dbengine)


@pytest.fixture
async def dbsession(dbsession_maker: AsyncSessionMaker) -> typing.AsyncGenerator[AsyncSession, None]:
    async with dbsession_maker() as dbsession:
        yield dbsession


@pytest.fixture(autouse=True)
async def setup_users(dbsession: AsyncSession) -> None:
    users = [
        User(id=1, name="user_01", email="01@user", profile=Profile(bio="bio_01")),
        User(id=2, name="user_02", email="02@user", profile=Profile(bio="bio_02")),
        User(id=3, name="user_03", email="03@user", profile=Profile(bio="bio_03")),
        User(id=4, name="user_04", email="04@user", profile=Profile(bio="bio_04")),
        User(id=5, name="user_05", email="05@user", profile=Profile(bio="bio_05")),
        User(id=6, name="user_06", email="06@user", profile=Profile(bio="bio_06")),
        User(id=7, name="user_07", email="07@user", profile=Profile(bio="bio_07")),
        User(id=8, name="user_08", email="08@user", profile=Profile(bio="bio_08")),
        User(id=9, name="user_09", email="09@user", profile=Profile(bio="bio_09")),
    ]
    dbsession.add_all(users)
    await dbsession.flush()
