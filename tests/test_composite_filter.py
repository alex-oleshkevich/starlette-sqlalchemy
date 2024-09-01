import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from starlette_sqlalchemy.repos import Repo, RepoFilter
from tests.models import Product


class ProductRepo(Repo[Product]):
    model_class = Product


@pytest.fixture
def product_repo(dbsession: AsyncSession) -> ProductRepo:
    return ProductRepo(dbsession)


class ById(RepoFilter[Product]):
    def __init__(self, id: int) -> None:
        self.id = id

    def apply(self, stmt: sa.Select[tuple[Product]]) -> sa.Select[tuple[Product]]:
        return stmt.filter(Product.id == self.id)


class ByName(RepoFilter[Product]):
    def __init__(self, name: str) -> None:
        self.name = name

    def apply(self, stmt: sa.Select[tuple[Product]]) -> sa.Select[tuple[Product]]:
        return stmt.filter(Product.name == self.name)


class TestCompositeFilter:
    async def test_filter(self, product_repo: ProductRepo) -> None:
        products = [
            Product(id=1, name="product_01"),
            Product(id=2, name="product_02"),
            Product(id=3, name="product_02"),
        ]
        product_repo.dbsession.add_all(products)
        await product_repo.dbsession.flush()

        filters = ByName("product_02") & ById(2)
        product = await product_repo.one(filters)
        assert product.id == 2
