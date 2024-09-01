import contextlib
import typing

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import Message, Receive, Send, Scope

from starlette_sqlalchemy.middleware import DbSessionMiddleware


async def empty_receive() -> Message:
    return {"type": "http.request", "body": b""}


async def empty_send(message: Message) -> None: ...


async def test_injects_dbsession() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        pass

    @contextlib.asynccontextmanager
    async def session_factory() -> typing.AsyncGenerator[AsyncSession, None]:
        yield AsyncSession()

    middleware = DbSessionMiddleware(app, session_factory, key="dbsession")
    scope: Scope = {}
    await middleware(scope, empty_receive, empty_send)
    assert "dbsession" in scope["state"]


async def test_injects_dbsession_with_custom_key() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        pass

    @contextlib.asynccontextmanager
    async def session_factory() -> typing.AsyncGenerator[AsyncSession, None]:
        yield AsyncSession()

    middleware = DbSessionMiddleware(app, session_factory, key="db")
    scope: Scope = {}
    await middleware(scope, empty_receive, empty_send)
    assert "db" in scope["state"]
