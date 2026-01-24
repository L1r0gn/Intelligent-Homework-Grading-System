# 启动 Redis 服务器 (端口 6380)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "redis-server --port 6380"

# 启动 Celery Worker
Start-Process powershell -ArgumentList "-NoExit", "-Command", "celery -A IntelligentHomeworkGradingSystem worker -l info --pool=solo"

# 启动 Django 开发服务器
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python manage.py runserver"

Write-Host "所有服务已启动..."

'''
powershell -ExecutionPolicy Bypass -File .\start_services.ps1
'''
