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
    engine_hint: Optional[str] = None


class MetricsOut(BaseModel):
    schema_version:             int = 2
    # core
    final_value:                Optional[float]
    total_return:               Optional[float]
    cagr:                       Optional[float]
    # risk
    volatility:                 Optional[float]
    downside_volatility:        Optional[float]
    sharpe_ratio:               Optional[float]
    sortino_ratio:              Optional[float]
    var_95:                     Optional[float]
    cvar_95:                    Optional[float]
    max_drawdown:               Optional[float]
    max_drawdown_duration_days: Optional[int]
    calmar_ratio:               Optional[float]
    # distribution
    omega_ratio:                Optional[float]
    tail_ratio:                 Optional[float]
    # trade quality
    win_rate:                   Optional[float]
    total_trades:               Optional[int]
    profit_factor:              Optional[float]
    avg_win:                    Optional[float]
    avg_loss:                   Optional[float]
    largest_win:                Optional[float]
    largest_loss:               Optional[float]
    avg_trade_duration_bars:    Optional[float]
    # exposure
    exposure_pct:               Optional[float]
    turnover:                   Optional[float]


class TradeOut(BaseModel):
    # v1 fields
    entry_price: float
    exit_price:  float
    pnl:         float
    side:        str
    fees:        float = 0.0
    slippage_cost: float = 0.0
    # v2 fields
    entry_time:  Optional[str] = None
    exit_time:   Optional[str] = None
    quantity:    Optional[float] = None
    pnl_pct:     Optional[float] = None
    bars_held:   Optional[int] = None
    mae:         Optional[float] = None
    mfe:         Optional[float] = None


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
