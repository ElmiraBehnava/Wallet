# celery.py

from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wallet.settings")

app = Celery("wallet")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks(["wallets.tasks"])

app.conf.update(
    broker_url="amqp://user:pass@hostname/vhost",
    result_backend="rpc://",
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="Asia/Tehran",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)
