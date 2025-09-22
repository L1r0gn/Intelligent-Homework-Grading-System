from .celery import app as celery_app
from celery import Celery
__all__ = ('celery_app',)

app = Celery('IntelligentHomeworkGradingSystem')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

'''
redis-server --port 6380
celery -A IntelligentHomeworkGradingSystem worker -l info --pool=solo
python manage.py runserver
'''