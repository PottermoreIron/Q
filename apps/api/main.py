from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import models.ohlcv_bar  # registers OHLCVBarRow with Base.metadata  # noqa: F401

from routers.auth import router as auth_router
from routers.data import router as data_router
from routers.health import router as health_router
from routers.backtest import router as backtest_router
from routers.strategy import router as strategy_router

app = FastAPI(
    title="Backtesting API",
    version="0.0.1",
    description="REST API for the backtesting application",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(data_router)
app.include_router(strategy_router)
app.include_router(backtest_router)


@app.exception_handler(Exception)
async def _engine_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    from services.engines.exceptions import EngineUnavailable
    if isinstance(exc, EngineUnavailable):
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    raise exc


@app.get("/")
async def root() -> dict:
    return {"message": "Backtesting API", "docs": "/docs"}
