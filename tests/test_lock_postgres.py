import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import Base, User
from app.schemas.user import DomainEnum, EnvironmentEnum, UserCreate
from app.services.user import create_user, lock_user

POSTGRES_TEST_DB_URL = os.getenv("TEST_POSTGRES_DB_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_DB_URL
    or not POSTGRES_TEST_DB_URL.startswith("postgresql+asyncpg://"),
    reason="Set TEST_POSTGRES_DB_URL=postgresql+asyncpg://... to run PostgreSQL lock tests",
)


@pytest_asyncio.fixture(scope="module")
async def postgres_engine():
    engine = create_async_engine(POSTGRES_TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def postgres_session_factory(postgres_engine):
    return sessionmaker(postgres_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_users(postgres_session_factory):
    async with postgres_session_factory() as session:
        await session.execute(delete(User))
        await session.commit()
    yield
    async with postgres_session_factory() as session:
        await session.execute(delete(User))
        await session.commit()


@pytest.mark.asyncio
async def test_lock_user_concurrent_postgres_returns_distinct_users(postgres_session_factory):
    async with postgres_session_factory() as session:
        await create_user(
            session,
            UserCreate(
                login=f"u1-{uuid.uuid4()}@example.com",
                password="secret-1",
                project_id=uuid.uuid4(),
                env=EnvironmentEnum.STAGE,
                domain=DomainEnum.REGULAR,
            ),
        )
        await create_user(
            session,
            UserCreate(
                login=f"u2-{uuid.uuid4()}@example.com",
                password="secret-2",
                project_id=uuid.uuid4(),
                env=EnvironmentEnum.STAGE,
                domain=DomainEnum.REGULAR,
            ),
        )

    async def lock_once() -> uuid.UUID:
        async with postgres_session_factory() as session:
            locked = await lock_user(session)
            return locked.id

    first_id, second_id = await asyncio.gather(lock_once(), lock_once())

    assert first_id != second_id

    async with postgres_session_factory() as session:
        result = await session.execute(select(User).order_by(User.created_at.asc()))
        users = list(result.scalars().all())

    assert len(users) == 2
    assert all(user.locktime is not None for user in users)
