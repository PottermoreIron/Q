from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class DataConfigIn(BaseModel):
    source: str
    symbol: str
    asset_class: str
    timeframe: str
    start_date: str
    end_date: str


class CreateRunIn(BaseModel):
    strategy_id: str
    data_config: DataConfigIn


class MetricsOut(BaseModel):
    sharpe_ratio:   Optional[float]
    sortino_ratio:  Optional[float]
    cagr:           Optional[float]
    max_drawdown:   Optional[float]
    win_rate:       Optional[float]
    total_trades:   Optional[int]
    profit_factor:  Optional[float]
    final_value:    Optional[float]


class TradeOut(BaseModel):
    entry_price: float
    exit_price: float
    pnl: float
    side: str


class BacktestRunOut(BaseModel):
    id: str
    strategy_id: Optional[str]
    strategy_name: str
    data_config: Dict[str, Any]
    status: str
    engine: Optional[str]
    metrics: Optional[MetricsOut]
    # sampled equity curve: list of [iso_timestamp, value] pairs
    equity_curve: Optional[List[List[Any]]]
    # trade list (capped at 500)
    trades: Optional[List[TradeOut]]
    error_message: Optional[str]
    log_output: Optional[str]
    as_of_time: Optional[str]
    created_at: str
    completed_at: Optional[str]

    model_config = {"from_attributes": True}
