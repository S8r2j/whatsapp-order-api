"""
Celery application configuration and beat schedule.

Worker command:
    celery -A app.tasks.celery_app worker --loglevel=info

Beat scheduler command (runs alongside the worker):
    celery -A app.tasks.celery_app beat --loglevel=info

Or combined (development only):
    celery -A app.tasks.celery_app worker --beat --loglevel=info
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# ── Celery application ────────────────────────────────────────────────────────

celery_app = Celery(
    "whatsapp_order_manager",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.order_tasks", "app.tasks.token_tasks"],
)

# ── General configuration ─────────────────────────────────────────────────────

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,            # Re-queue task if worker dies mid-execution
    worker_prefetch_multiplier=1,   # One task at a time per worker (safe for I/O tasks)
    task_default_retry_delay=60,    # Retry failed tasks after 60 seconds
    task_max_retries=3,
    result_expires=86400,           # Keep results for 24 hours
)

# ── Beat schedule (periodic tasks) ───────────────────────────────────────────

celery_app.conf.beat_schedule = {
    # 8PM UTC daily — send order summary to all shop owners
    "daily-order-summary": {
        "task": "app.tasks.order_tasks.send_daily_summaries",
        "schedule": crontab(hour=20, minute=0),
    },
    # Every Sunday at 2AM UTC — purge messages older than 90 days
    "weekly-message-cleanup": {
        "task": "app.tasks.order_tasks.cleanup_old_messages",
        "schedule": crontab(day_of_week=0, hour=2, minute=0),
    },
    "refresh-expiring-tokens": {
        "task": "app.tasks.token_tasks.refresh_expiring_tokens",
        "schedule": crontab(hour=2, minute=0),
    },
}
