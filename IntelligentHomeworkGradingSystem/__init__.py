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
    
cd Intelligent_Homework_Grading_System/
source venv/bin/activate

gunicorn --bind 0.0.0.0:8000 IntelligentHomeworkGradingSystem.wsgi:application

119.29.152.140

git clone https://L1r0gn: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@github.com/L1r0gn/Intelligent-Homework-Grading-System.git

pstree -ap|grep gunicorn
'''