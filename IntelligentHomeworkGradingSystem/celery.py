import os
from celery import Celery

# 设置 Django 的 settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IntelligentHomeworkGradingSystem.settings')
# 创建 Celery 应用
app = Celery('IntelligentHomeworkGradingSystem')
# 使用 Django settings.py 文件进行配置
app.config_from_object('django.conf:settings', namespace='CELERY')
# 自动发现所有注册的 Django app 下的 tasks.py 文件
app.autodiscover_tasks()