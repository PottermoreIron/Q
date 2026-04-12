"""
One-shot DB initialiser for local SQLite dev.
Creates all tables from SQLAlchemy metadata — skips Alembic migrations
which use PostgreSQL-specific SQL (DEFAULT now()).

Usage:
    python initdb.py
"""
import asyncio

from database import Base, engine
# Import models so their tables are registered on Base.metadata
from models import user, strategy, backtest_run  # noqa: F401


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")


if __name__ == "__main__":
    asyncio.run(main())
