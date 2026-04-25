"""CSV upload parsing — the only surviving piece of the old data_ingestion module."""

from __future__ import annotations

import io

from schemas.data import OHLCVBar


def parse_csv(content: bytes) -> tuple[list[OHLCVBar], list[str]]:
    """
    Parse a CSV file and return (bars, column_names).
    Expects columns: timestamp/date, open, high, low, close, volume (case-insensitive).
    """
    import pandas as pd

    df = pd.read_csv(io.BytesIO(content))
    columns = list(df.columns)
    bars = _df_to_bars(df)
    return bars, columns


def _df_to_bars(df: "pd.DataFrame") -> list[OHLCVBar]:
    import pandas as pd

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    if df.index.name and df.index.name.lower() in ("date", "datetime", "timestamp"):
        df = df.reset_index()
        ts_col = df.columns[0]
    else:
        ts_col = next(c for c in df.columns if c in ("date", "datetime", "timestamp", "time"))

    df[ts_col] = pd.to_datetime(df[ts_col])
    df["ts_ms"] = df[ts_col].astype("int64") // 1_000_000

    bars: list[OHLCVBar] = []
    for row in df.itertuples(index=False):
        bars.append(OHLCVBar(
            timestamp=int(row.ts_ms),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
        ))
    return bars
