"""
Data ingestion router.

GET  /data/search?q=BTC&asset_class=crypto          → symbol search
GET  /data/fetch?symbol=BTC/USDT&source=binance&... → fetch OHLCV preview (first 5 bars)
POST /data/upload                                   → upload CSV, returns file_key

source options: yahoo | binance | akshare | polygon | alpha_vantage | alpaca
Paid sources require the corresponding API keys in .env.
"""

import io
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile

from schemas.data import (
    AssetClass,
    CSVUploadOut,
    DataPreviewOut,
    SymbolSearchResult,
    Timeframe,
)
from services.data.csv import parse_csv
from services.data.registry import get_provider

router = APIRouter(prefix="/data", tags=["data"])

_SYMBOL_CATALOG: List[SymbolSearchResult] = [
    SymbolSearchResult(symbol="BTC/USDT",  name="Bitcoin / Tether",              asset_class="crypto",  exchange="Binance"),
    SymbolSearchResult(symbol="ETH/USDT",  name="Ethereum / Tether",             asset_class="crypto",  exchange="Binance"),
    SymbolSearchResult(symbol="SOL/USDT",  name="Solana / Tether",               asset_class="crypto",  exchange="Binance"),
    SymbolSearchResult(symbol="AAPL",      name="Apple Inc.",                     asset_class="stock",   exchange="NASDAQ"),
    SymbolSearchResult(symbol="TSLA",      name="Tesla Inc.",                     asset_class="stock",   exchange="NASDAQ"),
    SymbolSearchResult(symbol="MSFT",      name="Microsoft Corp.",                asset_class="stock",   exchange="NASDAQ"),
    SymbolSearchResult(symbol="SPY",       name="SPDR S&P 500 ETF",              asset_class="stock",   exchange="NYSE"),
    SymbolSearchResult(symbol="QQQ",       name="Invesco QQQ Trust",              asset_class="stock",   exchange="NASDAQ"),
    SymbolSearchResult(symbol="000001",    name="Ping An Bank (A-share)",         asset_class="stock",   exchange="SZSE"),
    SymbolSearchResult(symbol="600519",    name="Kweichow Moutai (A-share)",      asset_class="stock",   exchange="SSE"),
    SymbolSearchResult(symbol="HK00700",   name="Tencent Holdings (HK)",          asset_class="stock",   exchange="HKEX"),
    SymbolSearchResult(symbol="HK09988",   name="Alibaba Group (HK)",             asset_class="stock",   exchange="HKEX"),
    SymbolSearchResult(symbol="EUR/USD",   name="Euro / US Dollar",               asset_class="forex",   exchange="FX"),
    SymbolSearchResult(symbol="GBP/USD",   name="British Pound / US Dollar",      asset_class="forex",   exchange="FX"),
    SymbolSearchResult(symbol="ES=F",      name="E-mini S&P 500 Futures",         asset_class="futures", exchange="CME"),
    SymbolSearchResult(symbol="NQ=F",      name="E-mini NASDAQ-100 Futures",      asset_class="futures", exchange="CME"),
]


@router.get("/search", response_model=List[SymbolSearchResult])
async def symbol_search(
    q: str = Query(..., min_length=1),
    asset_class: Optional[AssetClass] = Query(None),
) -> List[SymbolSearchResult]:
    q_lower = q.lower()
    results = [
        s for s in _SYMBOL_CATALOG
        if (q_lower in s.symbol.lower() or q_lower in s.name.lower())
        and (asset_class is None or s.asset_class == asset_class)
    ]
    return results[:20]


@router.get("/fetch", response_model=DataPreviewOut)
async def fetch_preview(
    symbol: str = Query(...),
    asset_class: AssetClass = Query(...),
    timeframe: Timeframe = Query(...),
    start_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    source: Optional[str] = Query(None),
) -> DataPreviewOut:
    provider = get_provider(source, asset_class)
    try:
        bars = await provider.fetch_ohlcv(symbol, timeframe, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Data fetch failed: {exc}") from exc

    if not bars:
        raise HTTPException(status_code=404, detail="No data found for the given parameters")

    return DataPreviewOut(
        symbol=symbol,
        asset_class=asset_class,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        bar_count=len(bars),
        bars=bars[:5],
    )


@router.post("/upload", response_model=CSVUploadOut)
async def upload_csv(file: UploadFile) -> CSVUploadOut:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    try:
        bars, columns = parse_csv(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {exc}") from exc

    file_key = "local"
    try:
        from services.storage import upload_file
        file_key = upload_file(io.BytesIO(content), prefix="uploads", suffix=".csv")
    except Exception:
        pass  # Storage not configured in dev; carry on

    return CSVUploadOut(
        file_key=file_key,
        row_count=len(bars),
        detected_symbol=None,
        detected_timeframe=None,
        columns=columns,
    )
