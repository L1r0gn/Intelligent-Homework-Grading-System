# IntelligentHomeworkGradingSystem/celery.py
import os
from celery import Celery

# 设置默认的 Django 设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IntelligentHomeworkGradingSystem.settings')

app = Celery('IntelligentHomeworkGradingSystem')

# 使用 Django 的配置：所有 Celery 配置项以 CELERY_ 开头
app.config_from_object('django.conf:settings', namespace='CELERY')

# 从所有已注册的 Django app 中加载任务模块
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')