from celery import Celery
from config import settings

celery_app = Celery(
    "backtesting",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["services.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=270,   # 4.5 min soft limit
    task_time_limit=300,        # 5 min hard limit
    worker_prefetch_multiplier=1,
)
