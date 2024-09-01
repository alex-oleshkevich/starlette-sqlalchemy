from tests.conftest import dbsessionfrom sqlalchemy.ext.asyncio import AsyncSession

# Starlette-SQLAlchemy

SQLAlchemy integration.

![PyPI](https://img.shields.io/pypi/v/starlette_sqlalchemy)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/alex-oleshkevich/starlette_sqlalchemy/Lint)
![GitHub](https://img.shields.io/github/license/alex-oleshkevich/starlette_sqlalchemy)
![Libraries.io dependency status for latest release](https://img.shields.io/librariesio/release/pypi/starlette_sqlalchemy)
![PyPI - Downloads](https://img.shields.io/pypi/dm/starlette_sqlalchemy)
![GitHub Release Date](https://img.shields.io/github/release-date/alex-oleshkevich/starlette_sqlalchemy)

## Installation

Install `starlette_sqlalchemy` using PIP or poetry:

```bash
pip install starlette_sqlalchemy
# or
poetry add starlette_sqlalchemy
```

## Features

- query helper
- pagination
- session middleware
- model repository
- repository filters

## Usage

### Query helper

Query helper reduces amount of boilerplate code for SQLAlchemy queries.

```python
import sqlalchemy as sa

from starlette_sqlalchemy import query


class User: ...  # SQLAlchemy model


stmt = sa.select(User)


one_model = await query.one(stmt)

# fetch all models
many_models = await query.all(stmt)

# fetch model or return None if not found
nullable_model = await query.one_or_none(stmt)

# fetch model or raise exception if not found
model = await query.one_or_raise(stmt, ValueError("Model not found"))

# fetch model or return default value if not found
model = await query.one_or_default(stmt, User())

# test if model exists
exists = await query.exists(stmt)

# count models
count = await query.count(stmt)

# generate choices for select field (wtforms, etc)
choices = await query.choices(stmt, 'id', 'name')
```

### Pagination

The library includces a helper for pagination.

```python
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from starlette_sqlalchemy import PageNumberPaginator


class User: ...  # SQLAlchemy model


dbsession: AsyncSession = ...

stmt = sa.select(User)
paginator = PageNumberPaginator(dbsession)
page = await paginator.paginate(stmt, page=1, per_page=10)
for page_number in page.items:
    print(page_number)

```

### Session middleware

Session middleware automatically injects SQLAlchemy session into request state.

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine
from starlette.applications import Starlette
from starlette.middleware import Middleware

from starlette_sqlalchemy import DbSessionMiddleware

async_engine = create_async_engine("sqlite+aiosqlite:///db.sqlite")
session_factory = async_sessionmaker(async_engine, class_=AsyncSession)

app = Starlette(
    middleware=[
        Middleware(DbSessionMiddleware, session_factory=session_factory),
    ]
)


async def view(request):
    dbsession: AsyncSession = request.state.dbsession
    # do something with dbsession
```


### Model repository

Model repository is a high-level abstraction for working with models.
The purpose of the repository is to encapsulate the logic for fetching and storing models.
It best shines when used in larger projects where same model may be used in multiple context
like admin panel, public-facing API, etc.

```python
import sqlalchemy as sa

from starlette_sqlalchemy import Repo


class User:
    is_active: bool  # column


class APIUserRepo(Repo[User]):
    """Returns only active users"""
    model_class = User
    base_query = sa.select(User).where(User.is_active == True)


class AdminUserRepo(Repo[User]):
    """For admin panel, ignore active status and return all models"""
    model_class = User
    base_query = sa.select(User)


dbsession: AssertionError = ...
api_user_repo = APIUserRepo(dbsession)
admin_user_repo = AdminUserRepo(dbsession)

api_user_repo.all()  # returns  only active users
admin_user_repo.all()  # returns all users
```

Feel free to extend the repo with custom methods.


### Repository filters

Repository filters are composable and reusable SQLAchemy expressions.
Also, you can pack complex logic into a single filter.

This patterns prevents code duplication, makes the codebase more maintainable,
and reduces amount of silly bugs when you forget to filter out some data in some other place.

```python
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_sqlalchemy import Repo, RepoFilter


class User:
    email: str  # column


class UserRepo(Repo[User]):
    model_class = User


class ByEmailFilter(RepoFilter[User]):
    def __init__(self, email):
        self.email = email

    def apply(self, stmt):
        return stmt.where(User.email == self.email)


dbsession: AsyncSession = ...
repo = UserRepo(dbsession)
users = await repo.all(ByEmailFilter('root@localhost'))
```

#### Composing filters

Filters can be composed together to create complex queries.
The underlying statements will be merged together using `AND` operator.

```python
import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from starlette_sqlalchemy import Repo, RepoFilter


class User:
    is_active: bool  # column
    registered_at: datetime  # column


class UserRepo(Repo[User]):
    model_class = User


class OnlyIsActive(RepoFilter[User]):
    def apply(self, stmt):
        return stmt.where(User.is_active == True)


class ByRegistrationDate(RepoFilter[User]):
    def __init__(self, date):
        self.date = date

    def apply(self, stmt):
        return stmt.where(User.registered_at >= self.date)


dbsession: AsyncSession = ...
repo = UserRepo(dbsession)

filter_ = OnlyIsActive() & ByRegistrationDate('2022-01-01')
users = await repo.all(filter_)
```
