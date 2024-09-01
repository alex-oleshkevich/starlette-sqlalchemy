import typing

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import ASGIApp, Receive, Scope, Send


class DbSessionMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        session_factory: typing.Callable[[], typing.AsyncContextManager[AsyncSession]],
        key: str = "dbsession",
    ) -> None:
        self.app = app
        self.key = key
        self.session_factory = session_factory

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async with self.session_factory() as dbsession:
            scope.setdefault("state", {})
            scope["state"][self.key] = dbsession
            await self.app(scope, receive, send)
