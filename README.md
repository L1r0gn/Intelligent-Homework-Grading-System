# 智能作业批改系统

一个基于 Django 的智能作业批改系统，支持用户管理、题目管理、作业批改和知识追踪等功能。

## 技术栈

- **后端框架**: Django 4.2 + Django REST Framework
- **数据库**: MySQL
- **任务队列**: Celery + Redis
- **认证**: JWT (djangorestframework-simplejwt)
- **AI集成**: OpenAI API

## 项目结构

```
├── userManageModule/       # 用户管理模块
├── questionManageModule/   # 题目管理模块
├── gradingModule/          # 批改模块
├── assignmentAndClassModule/ # 作业与班级模块
├── BKTModule/              # 贝叶斯知识追踪模块
├── dkt_app/                # 深度知识追踪模块
└── IntelligentHomeworkGradingSystem/  # 项目配置
```

## 运行方法

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

创建 MySQL 数据库 `ihgs`，并在 `config.py` 中配置数据库密码。

### 3. 数据库迁移

```bash
python manage.py migrate
```

### 4. 启动服务

```bash
# 启动 Django 服务
python manage.py runserver

# 启动 Celery Worker (另一个终端)
celery -A IntelligentHomeworkGradingSystem worker -l info

# 启动 Redis (需要先安装 Redis)
redis-server
```

访问 http://127.0.0.1:8000 使用系统。
