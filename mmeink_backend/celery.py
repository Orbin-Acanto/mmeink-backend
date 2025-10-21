import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mmeink_backend.settings')

app = Celery('mmeink_backend')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-abandoned-chats-every-minute': {
        'task': 'chat.tasks.check_abandoned_chats',
        'schedule': crontab(minute='*/1'),
    },
    'generate-hourly-metrics': {
        'task': 'analytics.tasks.generate_hourly_metrics',
        'schedule': crontab(minute=0),
    },
    'generate-daily-metrics': {
        'task': 'analytics.tasks.generate_daily_metrics',
        'schedule': crontab(hour=0, minute=5),
    },
    'cleanup-old-sessions': {
        'task': 'chat.tasks.cleanup_old_sessions',
        'schedule': crontab(hour=2, minute=0),
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')