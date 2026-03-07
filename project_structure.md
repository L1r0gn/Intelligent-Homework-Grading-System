# 智能作业批改系统 - 项目结构概览

这是一个基于 **Django REST Framework** 构建的后端 Web 应用系统，支持微信小程序端访问。

---

## 1. 项目类型

**后端为主的 Web 应用系统** - 基于 Django REST Framework 构建的全栈系统，提供 RESTful API 服务和 Web 管理界面，同时支持微信小程序端访问。

---

## 2. 主要目录结构

```
IntelligentHomeworkGradingSystem/
│
├── IntelligentHomeworkGradingSystem/     # Django 项目核心配置目录
│   ├── settings.py                       # 项目配置文件
│   ├── urls.py                           # 主路由配置
│   ├── wsgi.py                           # WSGI 部署入口
│   ├── asgi.py                           # ASGI 部署入口
│   ├── celery.py                         # Celery 异步任务配置
│   ├── views.py                          # 核心视图（如 dashboard）
│   ├── models.py                         # 核心模型
│   └── templates/                        # 全局模板目录
│       └── dashboard.html
│
├── userManageModule/                     # 用户管理模块
│   ├── models.py                         # User、className、ClassTeacher 模型
│   ├── views.py                          # 用户注册、登录、班级管理视图
│   ├── urls.py                           # 用户模块路由
│   ├── admin.py                          # Admin 后台配置
│   ├── decorators.py                     # JWT 认证装饰器
│   ├── templates/                        # 用户模块模板
│   └── static/                           # 静态资源（Bootstrap等）
│
├── questionManageModule/                 # 题目管理模块
│   ├── models.py                         # Problem、ProblemType、Answer、KnowledgePoint 等模型
│   ├── views.py                          # 题目 CRUD、导入导出视图
│   ├── urls.py                           # 题目模块路由
│   ├── admin.py                          # Admin 后台配置
│   ├── management/                       # 自定义管理命令
│   │   └── commands/
│   │       └── import_questions.py       # 批量导入题目命令
│   └── templates/                        # 题目模块模板
│
├── gradingModule/                        # 作业批改模块
│   ├── models.py                         # Submission（提交记录）模型
│   ├── views.py                          # 批改相关视图
│   ├── urls.py                           # 批改模块路由
│   ├── serializers.py                    # REST Framework 序列化器
│   ├── forms.py                          # 表单定义
│   └── analysis_logic.py                 # 核心算法：掌握度计算服务
│
├── assignmentAndClassModule/             # 作业与班级管理模块
│   ├── models.py                         # Assignment、AssignmentStatus 模型
│   ├── views.py                          # 作业布置、状态管理视图
│   ├── urls.py                           # 作业模块路由
│   └── serializers.py                    # REST Framework 序列化器
│
├── BKTModule/                            # 贝叶斯知识追踪模块（AI 算法）
│   ├── views.py                          # BKT 相关 API（知识画像、预测等）
│   ├── urls.py                           # BKT 模块路由
│   ├── services.py                       # BKT 核心算法服务
│   ├── models.py                         # BKT 数据模型
│   └── data_migration.py                 # 数据迁移服务
│
├── dkt_app/                              # 深度知识追踪模块（AI 算法）
│   ├── views.py                          # DKT 掌握度预测视图
│   ├── urls.py                           # DKT 模块路由
│   ├── models.py                         # DKT 模型
│   ├── dkt_utils.py                      # DKT 工具函数
│   └── trained_models/                   # 训练好的模型文件
│       └── dkt_model.pth
│
├── media/                                # 媒体文件目录
│   ├── defaults/                         # 默认图片
│   ├── submissions/                      # 学生提交的图片
│   ├── problem_attachments/              # 题目附件
│   └── assignments/                      # 作业附件
│
├── static/                               # 静态文件目录
├── .venv/                                # Python 虚拟环境
├── .idea/                                # PyCharm 项目配置
├── .vscode/                              # VS Code 配置
│
├── manage.py                             # Django 管理脚本（项目入口）
├── config.py                             # 敏感配置（数据库密码、API密钥）
├── requirements.txt                      # 依赖包列表
├── requirements_py3.8.txt                # Python 3.8 依赖
└── requirements_py3.10.txt               # Python 3.10 依赖
```

---

## 3. 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | Django 4.2.21, Django REST Framework |
| **数据库** | MySQL (使用 PyMySQL 连接) |
| **认证系统** | JWT (rest_framework_simplejwt) + Session |
| **异步任务** | Celery + Redis |
| **AI/机器学习** | PyTorch (DKT模型), 贝叶斯知识追踪 (BKT) |
| **AI 批改** | OpenRouter API (LLM 接口) |
| **微信集成** | 微信小程序登录 (OpenID/UnionID) |
| **前端** | Django Templates + Bootstrap |
| **Python版本** | Python 3.8 / 3.10 兼容 |

---

## 4. 关键配置文件

| 文件路径 | 用途 |
|----------|------|
| `IntelligentHomeworkGradingSystem/settings.py` | Django 核心配置（数据库、应用、中间件、JWT、Celery等） |
| `IntelligentHomeworkGradingSystem/urls.py` | 主 URL 路由配置 |
| `config.py` | 敏感配置（数据库密码、API密钥） |
| `requirements.txt` | Python 依赖包列表 |
| `.vscode/settings.json` | VS Code 编辑器配置 |

---

## 5. 入口文件

| 文件 | 说明 |
|------|------|
| **`manage.py`** | Django 项目主入口，用于运行开发服务器和管理命令 |
| **`IntelligentHomeworkGradingSystem/wsgi.py`** | WSGI 部署入口（生产环境） |
| **`IntelligentHomeworkGradingSystem/asgi.py`** | ASGI 部署入口（异步应用） |

---

## 6. 核心功能模块说明

| 模块 | 功能描述 |
|------|----------|
| **userManageModule** | 用户注册登录、班级管理、角色权限（学生/教师/管理员） |
| **questionManageModule** | 题库管理、知识点管理、题目类型、标签系统 |
| **gradingModule** | 作业提交、AI 批改、掌握度计算 |
| **assignmentAndClassModule** | 作业布置、截止日期、作业状态追踪 |
| **BKTModule** | 贝叶斯知识追踪算法，预测学生知识掌握度 |
| **dkt_app** | 深度知识追踪（DKT）神经网络模型，知识状态预测 |

---

## 7. 数据模型关系概览

```
User (用户)
  ├── className (班级) - ManyToMany
  └── Submission (提交记录) - OneToMany

Problem (题目)
  ├── ProblemType (题目类型)
  ├── Subject (科目)
  ├── KnowledgePoint (知识点) - ManyToMany
  ├── ProblemContent (题目内容)
  ├── Answer (答案)
  └── Submission (提交记录) - OneToMany

Assignment (作业)
  ├── Problem (题目)
  ├── className (班级)
  └── AssignmentStatus (学生作业状态)
      └── Submission (提交记录)

StudentMastery (学生掌握度)
  ├── User (学生)
  └── KnowledgePoint (知识点)
```

---

## 8. API 路由结构

```
/admin/                    # Django Admin 后台
/user/                     # 用户模块 API
/question/                 # 题目模块 API
/grading/                  # 批改模块 API
/assignment/               # 作业模块 API
/bkt/                      # BKT 知识追踪 API
/dkt/                      # DKT 知识追踪 API
/register/                 # 用户注册
/class/                    # 班级管理
```

---

## 9. 项目特点

这是一个功能完整的智能教育系统，整合了：

- 传统 Web 管理
- 微信小程序端
- AI 知识追踪算法（BKT/DKT）

主要用于作业批改和学生知识掌握度分析。
