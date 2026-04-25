"""
Shared pytest fixtures.

Integration tests that hit a real database use the `db` fixture, which is
backed by a testcontainers PostgreSQL container when Docker is available.

Without Docker (local dev without Docker Desktop, CI without DinD), the
`db` fixture is unavailable and any test that uses it is skipped with a
clear message — "Docker required for integration tests."

Unit tests that don't use the `db` fixture are never affected.
"""

from __future__ import annotations

import os
import subprocess
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database import Base

# ---------------------------------------------------------------------------
# Docker availability check
# ---------------------------------------------------------------------------

def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


_DOCKER_AVAILABLE = _docker_available()
_skip_no_docker = pytest.mark.skipif(
    not _DOCKER_AVAILABLE,
    reason="Docker not available — integration tests require a running Docker daemon",
)


# ---------------------------------------------------------------------------
# Session-scoped PostgreSQL container (started once per pytest session)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def pg_container():
    """Start a postgres:15-alpine container for the entire test session."""
    if not _DOCKER_AVAILABLE:
        pytest.skip("Docker not available")

    from testcontainers.postgres import PostgresContainer  # type: ignore

    with PostgresContainer("postgres:15-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def pg_url(pg_container) -> str:
    """Async-compatible connection URL for the container."""
    sync_url: str = pg_container.get_connection_url()
    # testcontainers returns a psycopg2 URL; we need asyncpg
    return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    )


@pytest.fixture(scope="session")
async def db_engine(pg_url: str):
    """
    Create tables via alembic upgrade head once for the whole session,
    then yield the engine.
    """
    import alembic.config

    from alembic.config import Config

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url.replace("+asyncpg", ""))

    # Run migrations synchronously (alembic uses sync connections)
    alembic.config.command.upgrade(cfg, "head")

    engine = create_async_engine(pg_url, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Per-test async session. Truncates all tables after each test so tests
    are isolated without the overhead of recreating the schema.
    """
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async with factory() as session:
        yield session

    # Truncate all user tables between tests
    async with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# ---------------------------------------------------------------------------
# Backwards-compatible SQLite fixture (unit tests that haven't been migrated)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
async def sqlite_engine():
    """
    Temporary SQLite engine for tests that are explicitly not integration tests.
    This fixture exists only during Task 0.E migration — once all tests use `db`,
    this should be deleted.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def sqlite_session(sqlite_engine):
    factory = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
