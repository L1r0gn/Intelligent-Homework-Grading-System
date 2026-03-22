from .celery import app as celery_app
from celery import Celery
__all__ = ('celery_app',)

app = Celery('IntelligentHomeworkGradingSystem')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

'''
#本地部署
redis-server --port 6380
celery -A IntelligentHomeworkGradingSystem worker -l info --pool=solo
python manage.py runserver

# 部署#本地部署
# redis-server --port 6380
# celery -A IntelligentHomeworkGradingSystem worker -l info --pool=solo
# python manage.py runserver
# cd Intelligent_Homework_Grading_System/
cd Intelligent-Homework-Grading-System
source venv/bin/activate
gunicorn --bind 0.0.0.0:8000 IntelligentHomeworkGradingSystem.wsgi:application

# 服务器地址
119.29.152.140

# 从服务器克隆项目
git clone https://L1r0gn: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@github.com/L1r0gn/Intelligent-Homework-Grading-System.git

# 查看gunicorn进程
pstree -ap|grep gunicorn
# 终止gunicorn进程
kill -9 <pid>
'''