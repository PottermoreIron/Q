from typing import List, Literal, Optional
from pydantic import BaseModel


AssetClass = Literal["crypto", "stock", "forex", "futures", "options"]
Timeframe = Literal["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
DataSource = Literal["csv", "yahoo", "binance", "alpha_vantage", "polygon", "alpaca"]


class SymbolSearchResult(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass
    exchange: str


class OHLCVBar(BaseModel):
    timestamp: int  # Unix ms
    open: float
    high: float
    low: float
    close: float
    volume: float


class DataPreviewOut(BaseModel):
    symbol: str
    asset_class: AssetClass
    timeframe: Timeframe
    start_date: str
    end_date: str
    bar_count: int
    bars: List[OHLCVBar]


class CSVUploadOut(BaseModel):
    file_key: str
    row_count: int
    detected_symbol: Optional[str]
    detected_timeframe: Optional[str]
    columns: List[str]
