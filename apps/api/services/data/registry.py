"""
Data provider registry.

Single entry point for the rest of the codebase. Callers ask for a provider
by (source, asset_class) and receive a DataProvider — they never import a
concrete provider class directly.
"""
from __future__ import annotations

from schemas.data import AssetClass
from services.data.protocol import DataProvider
from services.data.providers.akshare import AkShareProvider
from services.data.providers.alpha_vantage import AlphaVantageProvider
from services.data.providers.alpaca import AlpacaProvider
from services.data.providers.binance import BinanceProvider
from services.data.providers.polygon import PolygonProvider
from services.data.providers.yahoo import YahooProvider


def get_provider(source: str | None, asset_class: AssetClass) -> DataProvider:
    """
    Return the appropriate DataProvider for the given (source, asset_class) pair.

    Explicit source always wins. Asset-class fallback applies when source is absent:
      crypto → Binance
      all others → Yahoo Finance
    """
    src = (source or "").lower().strip()

    if src == "polygon":
        return PolygonProvider()
    if src == "alpha_vantage":
        return AlphaVantageProvider()
    if src == "alpaca":
        return AlpacaProvider()
    if src == "akshare":
        return AkShareProvider()
    if src == "binance" or (not src and asset_class == "crypto"):
        return BinanceProvider()

    # Default: Yahoo Finance (stocks, ETFs, indices, forex)
    return YahooProvider()
