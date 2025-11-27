from celery import Celery
from src.core.config.settings import settings

celery_app = Celery(
    "dev_agent_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.services.celery_worker.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
)
