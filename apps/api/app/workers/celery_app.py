from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_job_hunter",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "sheets-sync-periodic": {
            "task": "app.workers.tasks.sheets_sync_task",
            "schedule": 600.0,  # 10 minutes
        },
        "gmail-reconcile-periodic": {
            "task": "app.workers.tasks.gmail_reconcile_task",
            "schedule": 900.0,  # 15 minutes
        },
        # Discover + draft 4x/day so the 30/day send quota can refill continuously.
        "discovery-outreach-0600": {
            "task": "app.workers.tasks.daily_outreach_task",
            "schedule": crontab(hour=6, minute=0),
        },
        "discovery-outreach-1200": {
            "task": "app.workers.tasks.daily_outreach_task",
            "schedule": crontab(hour=12, minute=0),
        },
        "discovery-outreach-1600": {
            "task": "app.workers.tasks.daily_outreach_task",
            "schedule": crontab(hour=16, minute=0),
        },
        "discovery-outreach-2100": {
            "task": "app.workers.tasks.daily_outreach_task",
            "schedule": crontab(hour=21, minute=0),
        },
        # Hourly flush so emails go out in each recipient country's working hours.
        "hourly-outreach-send": {
            "task": "app.workers.tasks.hourly_outreach_send_task",
            "schedule": crontab(minute=15),
        },
    },
)
