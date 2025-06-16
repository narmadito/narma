import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'narma.settings')

app = Celery('narma')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

from celery import shared_task

@shared_task
def debug_task(x,y):
    return x+y
