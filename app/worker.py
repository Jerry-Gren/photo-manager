"""
Celery worker configuration.

This module initializes the Celery application, setting up the broker
and backend connections based on environment variables.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Load configuration from environment variables
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://broker:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://broker:6379/1")

# Initialize Celery app
celery_app = Celery(
    "worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configuration updates
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)

# Celery Beat Configuration
celery_app.conf.beat_schedule = {
    "run-rag-indexer-every-minute": {
        "task": "app.tasks.build_rag_index",
        "schedule": 60.0,  # run per 60 secs
    },
}

# Auto-discover tasks in the 'app.tasks' module
celery_app.autodiscover_tasks(["app.tasks"])