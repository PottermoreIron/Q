"""
Schema-diff CI gate.

Runs `alembic upgrade head` then `alembic check` against a real PostgreSQL
container.  Both commands run in subprocesses to avoid the local alembic/
migrations directory shadowing the installed alembic package.

DATABASE_URL is injected via env var so env.py picks it up through Settings.

Requires: testcontainers[postgresql] (added in Task 0.E), Docker.
Skipped when either is absent.
"""

import os
import shutil
import subprocess

import pytest

try:
    from testcontainers.postgres import PostgresContainer
    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False


def _docker_available() -> bool:
    return shutil.which("docker") is not None and subprocess.call(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ) == 0


@pytest.mark.skipif(
    not HAS_TESTCONTAINERS or not _docker_available(),
    reason="testcontainers or Docker not available",
)
def test_schema_matches_models() -> None:
    """alembic upgrade head + alembic check must both exit 0."""
    alembic_bin = shutil.which("alembic")
    if not alembic_bin:
        pytest.skip("alembic CLI not found on PATH")

    with PostgresContainer("postgres:15-alpine") as pg:
        # Convert sync psycopg2 URL → asyncpg URL for env.py
        db_url = pg.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://", 1
        ).replace("postgresql://", "postgresql+asyncpg://", 1)

        env = {**os.environ, "DATABASE_URL": db_url}

        result = subprocess.run(
            [alembic_bin, "upgrade", "head"],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0, (
            f"alembic upgrade head failed:\n{result.stdout}\n{result.stderr}"
        )

        result = subprocess.run(
            [alembic_bin, "check"],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0, (
            f"Schema drift — run `alembic revision --autogenerate`:\n"
            f"{result.stdout}\n{result.stderr}"
        )
