import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database import Base, get_db
from main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="module")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession):
    async def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── Compiler tests (no DB needed) ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compile_empty_blocks(client):
    resp = await client.post("/strategies/compile", json={"name": "x", "blocks": []})
    assert resp.status_code == 200
    code = resp.json()["python_code"]
    assert "def run" in code
    assert "entries" in code


@pytest.mark.asyncio
async def test_compile_ema_crossover(client):
    resp = await client.post("/strategies/compile", json={
        "name": "EMA Crossover",
        "blocks": [
            {"id": "1", "type": "indicator", "name": "ema", "params": {"period": 10}},
            {"id": "2", "type": "indicator", "name": "ema", "params": {"period": 30}},
            {"id": "3", "type": "condition", "name": "ema_crossover",
             "params": {"fast_period": 10, "slow_period": 30}},
        ],
    })
    assert resp.status_code == 200
    code = resp.json()["python_code"]
    assert "ema_10" in code
    assert "ema_30" in code
    assert "entries" in code


# ── Validator tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_valid_code(client):
    code = (
        "import pandas as pd\n"
        "def run(ohlcv):\n"
        "    close = ohlcv['close']\n"
        "    entries = close > close.shift(1)\n"
        "    exits = close < close.shift(1)\n"
        "    return {'entries': entries, 'exits': exits}\n"
    )
    resp = await client.post("/strategies/validate", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_validate_missing_run_fn(client):
    resp = await client.post("/strategies/validate", json={"code": "x = 1\n"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert any("run" in e for e in data["errors"])


@pytest.mark.asyncio
async def test_validate_forbidden_import(client):
    code = "import os\ndef run(ohlcv):\n    return {}\n"
    resp = await client.post("/strategies/validate", json={"code": code})
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


@pytest.mark.asyncio
async def test_validate_syntax_error(client):
    resp = await client.post("/strategies/validate", json={"code": "def run(\n"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert any("Syntax" in e for e in data["errors"])


# ── CRUD tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_get_strategy(client):
    resp = await client.post("/strategies", json={
        "name": "My EMA Strategy",
        "blocks": [
            {"id": "1", "type": "indicator", "name": "ema", "params": {"period": 20}},
            {"id": "2", "type": "condition", "name": "price_above_sma",
             "params": {"period": 200}},
        ],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My EMA Strategy"
    assert "python_code" in data
    assert data["python_code"] is not None

    sid = data["id"]
    get_resp = await client.get(f"/strategies/{sid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == sid


@pytest.mark.asyncio
async def test_list_strategies(client):
    await client.post("/strategies", json={"name": "Strategy A", "blocks": []})
    await client.post("/strategies", json={"name": "Strategy B", "blocks": []})
    resp = await client.get("/strategies")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_update_strategy(client):
    create = await client.post("/strategies", json={"name": "Old Name", "blocks": []})
    sid = create.json()["id"]
    patch = await client.patch(f"/strategies/{sid}", json={"name": "New Name"})
    assert patch.status_code == 200
    assert patch.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_strategy(client):
    create = await client.post("/strategies", json={"name": "To Delete", "blocks": []})
    sid = create.json()["id"]
    del_resp = await client.delete(f"/strategies/{sid}")
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/strategies/{sid}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_strategy(client):
    resp = await client.get("/strategies/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
