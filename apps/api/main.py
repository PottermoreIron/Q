from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.auth import router as auth_router
from routers.data import router as data_router
from routers.health import router as health_router

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


@app.get("/")
async def root() -> dict:
    return {"message": "Backtesting API", "docs": "/docs"}
