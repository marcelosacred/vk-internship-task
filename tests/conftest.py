import os
import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = os.getenv("TEST_DB_URL", "sqlite+aiosqlite:///:memory:")
os.environ["DB_URL"] = TEST_DB_URL

from app.main import app
from app.db.database import get_db
from app.models.user import Base


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
def user_data():
    return {
        "login": "vlad@vlad.com",
        "password": "vlad123paswordhello",
        "project_id": str(uuid.uuid4()),
        "env": "stage",
        "domain": "regular",
    }
