# 智能作业批改系统 - API 接口文档

## 目录
1. [API 概述](#api-概述)
2. [用户管理模块](#1-用户管理模块-usermanagemodule)
3. [题目管理模块](#2-题目管理模块-questionmanagemodule)
4. [批改模块](#3-批改模块-gradingmodule)
5. [作业与班级模块](#4-作业与班级模块-assignmentandclassmodule)
6. [BKT模块](#5-bkt模块-bktmodule)
7. [DKT模块](#6-dkt模块-dkt_app)
8. [核心模块](#7-核心模块-intelligenthomeworkgradingsystem)

---

## API 概述

### 基础信息
- **基础URL**: `http://域名/`
- **数据格式**: JSON
- **字符编码**: UTF-8

### 认证方式

| 认证类型 | 适用场景 | 使用方式 |
|----------|----------|----------|
| **JWT认证** | 微信小程序API | 请求头: `Authorization: Bearer {access_token}` |
| **Session认证** | 网页端管理系统 | 通过登录获取session |

### 用户权限等级

| user_attribute | 角色 |
|----------------|------|
| 0 | 访客 |
| 1 | 学生 |
| 2 | 教师 |
| 3 | 管理员 |
| 4 | 超级管理员 |

### 通用响应格式

**成功响应:**
```json
{
    "success": true,
    "message": "操作成功",
    "data": { ... }
}
```

**错误响应:**
```json
{
    "success": false,
    "error": "错误信息"
}
```

---

## 1. 用户管理模块 (userManageModule)

### 1.1 网页端用户登录

| 项目 | 内容 |
|------|------|
| **URL** | `/user/login/` |
| **方法** | `GET`, `POST` |
| **功能** | 网页端用户登录 |

**请求参数 (POST):**
```
username: 用户名
password: 密码
```

**响应:**
- 成功: 重定向到用户列表页
- 失败: 返回登录页面并显示错误

---

### 1.2 网页端用户注销

| 项目 | 内容 |
|------|------|
| **URL** | `/user/logout/` |
| **方法** | `GET` |
| **功能** | 用户注销登录 |

**响应:** 重定向到登录页面

---

### 1.3 个人中心

| 项目 | 内容 |
|------|------|
| **URL** | `/user/profile/` |
| **方法** | `GET`, `POST` |
| **功能** | 用户查看和编辑个人基本信息 |
| **认证** | 需要登录 |

**请求参数 (POST):**
```
nickName: 昵称
phone: 手机号
```

**响应:** 成功后重定向到个人中心页面

---

### 1.4 用户列表 (管理员)

| 项目 | 内容 |
|------|------|
| **URL** | `/user/list/` |
| **方法** | `GET` |
| **功能** | 显示所有用户列表，支持搜索和筛选 |
| **认证** | 管理员权限 (user_attribute >= 3) |

**请求参数 (Query):**
```
q: 搜索关键词
attribute: 用户属性筛选
gender: 性别筛选
```

**响应:** 渲染用户列表HTML页面

---

### 1.5 编辑用户

| 项目 | 内容 |
|------|------|
| **URL** | `/user/edit/<int:user_id>/` |
| **方法** | `GET`, `POST` |
| **功能** | 管理员编辑用户信息 |
| **认证** | 管理员权限 |

**路径参数:**
```
user_id: 用户ID
```

**请求参数 (POST):**
```
nickName: 昵称
password: 密码
username: 用户名
phone: 手机号
gender: 性别
userAttribute: 用户属性
classInfo: 班级信息
```

**响应:** 成功后重定向到用户列表

---

### 1.6 删除用户

| 项目 | 内容 |
|------|------|
| **URL** | `/user/delete/<int:user_id>/` |
| **方法** | `POST` |
| **功能** | 管理员删除指定用户 |
| **认证** | 管理员权限 |

**路径参数:**
```
user_id: 用户ID
```

**响应:** 重定向到用户列表页面

---

### 1.7 添加用户

| 项目 | 内容 |
|------|------|
| **URL** | `/user/add/` |
| **方法** | `GET`, `POST` |
| **功能** | 管理员添加新用户 |
| **认证** | 管理员权限 |

**请求参数 (POST):** 用户表单数据

**响应:** 成功后重定向到用户列表

---

### 1.8 用户个人信息更新 API

| 项目 | 内容 |
|------|------|
| **URL** | `/user/api/profile/update/` |
| **方法** | `PUT`, `PATCH` |
| **功能** | REST API - 更新用户个人信息 |
| **认证** | JWT认证 |

**请求头:**
```
Authorization: Bearer {token}
```

**请求体 (JSON):**
```json
{
    "nickName": "昵称",
    "phone": "手机号",
    "gender": 1
}
```

**响应 (JSON):**
```json
{
    "message": "个人信息更新成功",
    "data": {
        "id": 1,
        "username": "user001",
        "nickName": "昵称"
    }
}
```

---

### 1.9 班级列表 (网页端)

| 项目 | 内容 |
|------|------|
| **URL** | `/user/class/list/` |
| **方法** | `GET` |
| **功能** | 显示所有班级列表 |
| **认证** | 管理员权限 |

**请求参数 (Query):**
```
q: 搜索关键词
grade: 年级筛选
```

**响应:** 渲染班级列表HTML页面

---

### 1.10 我的班级列表

| 项目 | 内容 |
|------|------|
| **URL** | `/user/class/my/` |
| **方法** | `GET` |
| **功能** | 显示当前用户所在的班级列表 |
| **认证** | 需要登录 |

**响应 (JSON):**
```json
{
    "results": [
        {"id": 1, "name": "高三一班"},
        {"id": 2, "name": "高三二班"}
    ]
}
```

---

### 1.11 创建班级 (网页端)

| 项目 | 内容 |
|------|------|
| **URL** | `/user/class/create/` |
| **方法** | `GET`, `POST` |
| **功能** | 教师创建新班级 |
| **认证** | 教师权限 (user_attribute >= 2) |

**请求参数 (POST):** 班级表单数据

**响应:** 成功后重定向到班级列表

---

### 1.12 编辑班级

| 项目 | 内容 |
|------|------|
| **URL** | `/user/class/edit/<int:class_id>/` |
| **方法** | `GET`, `POST` |
| **功能** | 编辑班级信息 |
| **认证** | 管理员权限 |

**路径参数:**
```
class_id: 班级ID
```

---

### 1.13 删除班级

| 项目 | 内容 |
|------|------|
| **URL** | `/user/class/delete/<int:class_id>/` |
| **方法** | `POST` |
| **功能** | 删除班级 |
| **认证** | 管理员权限 |

**路径参数:**
```
class_id: 班级ID
```

---

### 1.14 班级详情

| 项目 | 内容 |
|------|------|
| **URL** | `/user/class/detail/<int:class_id>/` |
| **方法** | `GET` |
| **功能** | 查看班级详情、学生和教师列表 |
| **认证** | 管理员权限 |

**路径参数:**
```
class_id: 班级ID
```

---

### 1.15 添加学生到班级

| 项目 | 内容 |
|------|------|
| **URL** | `/user/class/student/add/<int:class_id>/` |
| **方法** | `POST` |
| **功能** | 将学生添加到班级 |
| **认证** | 管理员权限 |

**路径参数:**
```
class_id: 班级ID
```

**请求参数 (POST):**
```
student: 学生ID
```

---

### 1.16 从班级移除学生

| 项目 | 内容 |
|------|------|
| **URL** | `/user/class/student/remove/<int:class_id>/<int:student_id>/` |
| **方法** | `POST` |
| **功能** | 从班级中移除学生 |
| **认证** | 管理员权限 |

**路径参数:**
```
class_id: 班级ID
student_id: 学生ID
```

---

### 1.17 添加教师到班级

| 项目 | 内容 |
|------|------|
| **URL** | `/user/class/teacher/add/<int:class_id>/` |
| **方法** | `POST` |
| **功能** | 添加任课教师到班级 |
| **认证** | 管理员权限 |

**路径参数:**
```
class_id: 班级ID
```

**请求参数 (POST):**
```
teacher: 教师ID
subject: 科目
```

---

### 1.18 从班级移除教师

| 项目 | 内容 |
|------|------|
| **URL** | `/user/class/teacher/remove/<int:class_id>/<int:teacher_id>/` |
| **方法** | `POST` |
| **功能** | 移除任课教师 |
| **认证** | 管理员权限 |

**路径参数:**
```
class_id: 班级ID
teacher_id: ClassTeacher关系ID
```

---

### 1.19 通过班级码加入班级 (网页端)

| 项目 | 内容 |
|------|------|
| **URL** | `/user/class/join/` |
| **方法** | `GET`, `POST` |
| **功能** | 学生通过班级码加入班级 |
| **认证** | 学生权限 (user_attribute == 1) |

**请求参数 (POST):**
```
class_code: 班级邀请码
```

**响应:** 成功后重定向到我的班级列表

---

### 1.20 搜索学生 API

| 项目 | 内容 |
|------|------|
| **URL** | `/user/api/student/search/` |
| **方法** | `GET` |
| **功能** | 搜索学生，用于下拉选择 |
| **认证** | 需要登录 |

**请求参数 (Query):**
```
q: 搜索关键词
```

**响应 (JSON):**
```json
{
    "results": [
        {"id": 1, "text": "张三"},
        {"id": 2, "text": "李四"}
    ]
}
```

---

### 1.21 微信小程序登录

| 项目 | 内容 |
|------|------|
| **URL** | `/user/wx/login/` |
| **方法** | `POST` |
| **功能** | 微信小程序登录，通过code换取openid并返回JWT Token |

**请求体 (JSON):**
```json
{
    "code": "微信登录code"
}
```

**响应 (JSON):**
```json
{
    "refresh": "refresh_token",
    "access": "access_token",
    "user_id": 1
}
```

**错误响应:**
```json
{
    "error": "登录失败: 无效的code"
}
```

---

### 1.22 微信小程序获取用户详情

| 项目 | 内容 |
|------|------|
| **URL** | `/user/wx/list/<int:user_id>/` |
| **方法** | `GET` |
| **功能** | 获取指定用户的详细信息 |
| **认证** | JWT认证 |

**路径参数:**
```
user_id: 用户ID
```

**响应 (JSON):**
```json
{
    "data": {
        "id": 1,
        "username": "user001",
        "nickName": "昵称",
        "gender": 1,
        "phone": "13800138000",
        "avatarUrl": "头像URL",
        "userAttribute": 1
    }
}
```

---

### 1.23 微信小程序编辑用户信息

| 项目 | 内容 |
|------|------|
| **URL** | `/user/wx/edit/<int:user_id>` |
| **方法** | `GET`, `POST` |
| **功能** | 获取或更新用户信息 |
| **认证** | JWT认证 |

**路径参数:**
```
user_id: 用户ID
```

**请求体 (POST JSON):**
```json
{
    "gender": 1,
    "attribute": 1,
    "phone": "13800138000",
    "nickName": "昵称",
    "avatarUrl": "头像URL",
    "class_in_id": 1
}
```

**响应 (JSON):**
```json
{
    "success": true,
    "user": {
        "id": 1,
        "nickName": "昵称"
    }
}
```

---

### 1.24 微信小程序学生加入班级

| 项目 | 内容 |
|------|------|
| **URL** | `/user/wx/userJoinClass/` |
| **方法** | `POST` |
| **功能** | 学生通过班级码加入班级 |
| **认证** | JWT认证 + 学生权限 |

**请求体 (JSON):**
```json
{
    "class_code": "ABC123"
}
```

**响应 (JSON):**
```json
{
    "success": true,
    "message": "成功加入班级",
    "class_info": {
        "id": 1,
        "name": "高三一班",
        "code": "ABC123"
    }
}
```

---

### 1.25 创建班级 API (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/class/create/` |
| **方法** | `POST` |
| **功能** | 微信端创建班级 |
| **认证** | JWT认证 + 教师权限 (user_attribute >= 2) |

**请求体 (JSON):**
```json
{
    "name": "班级名称"
}
```

**响应 (JSON):**
```json
{
    "success": true,
    "message": "班级创建成功",
    "current_class": {
        "id": 1,
        "name": "班级名称",
        "code": "ABC123"
    },
    "user_classes": [...]
}
```

---

### 1.26 班级详情 API

| 项目 | 内容 |
|------|------|
| **URL** | `/class/<int:class_id>/` |
| **方法** | `GET` |
| **功能** | 获取班级详细信息 |
| **认证** | JWT认证 |

**路径参数:**
```
class_id: 班级ID
```

**响应 (JSON):**
```json
{
    "data": {
        "id": 1,
        "name": "高三一班",
        "code": "ABC123",
        "student_count": 50,
        "created_at": "2024-01-01"
    }
}
```

---

### 1.27 获取班级成员

| 项目 | 内容 |
|------|------|
| **URL** | `/class/<int:class_id>/members/` |
| **方法** | `GET` |
| **功能** | 获取指定班级的成员列表 |
| **认证** | JWT认证 |

**路径参数:**
```
class_id: 班级ID
```

**响应 (JSON):**
```json
{
    "data": [
        {
            "id": 1,
            "name": "张三",
            "avatar": "头像URL",
            "uid": "2024001"
        }
    ]
}
```

---

### 1.28 学生退出班级

| 项目 | 内容 |
|------|------|
| **URL** | `/class/class_id=<int:class_id>/quit/` |
| **方法** | `POST` |
| **功能** | 学生退出班级 |
| **认证** | JWT认证 |

**路径参数:**
```
class_id: 班级ID
```

**响应 (JSON):**
```json
{
    "success": true,
    "message": "成功退出班级"
}
```

---

### 1.29 用户注册 (网页端)

| 项目 | 内容 |
|------|------|
| **URL** | `/register/` |
| **方法** | `GET`, `POST` |
| **功能** | 用户公开注册 |

**请求参数 (POST):** 用户表单数据

**响应:** 成功后重定向到用户列表

---

## 2. 题目管理模块 (questionManageModule)

### 2.1 题目列表

| 项目 | 内容 |
|------|------|
| **URL** | `/question/list/` |
| **方法** | `GET` |
| **功能** | 显示题目列表，支持搜索和筛选 |
| **认证** | 需要登录 |

**请求参数 (Query):**
```
q: 搜索关键词
subject: 科目ID
type: 题型ID
difficulty: 难度
```

**响应:** 渲染题目列表HTML页面

---

### 2.2 创建题目

| 项目 | 内容 |
|------|------|
| **URL** | `/question/create/` |
| **方法** | `GET`, `POST` |
| **功能** | 创建新题目 |
| **认证** | 管理员权限 |

**请求参数 (POST):**
```
title: 题目标题
content: 题目内容
difficulty: 难度等级
problem_type: 题型ID
subject: 科目ID
knowledge_points: 知识点ID数组
points: 分值
estimated_time: 预计用时
answer_content: 答案内容
answer_explanation: 答案解析
```

**响应:** 成功后重定向到题目列表

---

### 2.3 题目详情

| 项目 | 内容 |
|------|------|
| **URL** | `/question/detail/<int:question_id>/` |
| **方法** | `GET` |
| **功能** | 查看题目详情 |
| **认证** | 需要登录 |

**路径参数:**
```
question_id: 题目ID
```

**响应:** 渲染题目详情HTML页面

---

### 2.4 更新题目

| 项目 | 内容 |
|------|------|
| **URL** | `/question/update/<int:question_id>/` |
| **方法** | `GET`, `POST` |
| **功能** | 编辑题目信息 |
| **认证** | 管理员权限 |

**路径参数:**
```
question_id: 题目ID
```

**请求参数 (POST):** 同创建题目

---

### 2.5 删除题目

| 项目 | 内容 |
|------|------|
| **URL** | `/question/delete/<int:question_id>/` |
| **方法** | `POST` |
| **功能** | 删除题目 |
| **认证** | 管理员权限 |

**路径参数:**
```
question_id: 题目ID
```

---

### 2.6 批量导入JSON题目

| 项目 | 内容 |
|------|------|
| **URL** | `/question/batch-import-json/` |
| **方法** | `GET`, `POST` |
| **功能** | 上传JSON文件批量导入题目 |
| **认证** | 管理员权限 |

**请求参数 (POST):**
```
json_file: JSON文件
default_subject_id: 默认科目ID
default_problem_type_id: 默认题型ID
```

**响应:** 成功后重定向到审核页面

---

### 2.7 题目导入审核

| 项目 | 内容 |
|------|------|
| **URL** | `/question/questions/import/review/` |
| **方法** | `GET`, `POST` |
| **功能** | 审核并确认批量导入的题目 |
| **认证** | 管理员权限 |

**响应:** 渲染审核页面

---

### 2.8 批量操作题目

| 项目 | 内容 |
|------|------|
| **URL** | `/question/questions/batch-action/` |
| **方法** | `POST` |
| **功能** | 批量删除/启用/禁用题目 |
| **认证** | 管理员权限 |

**请求参数 (POST):**
```
action: delete/disable/enable
selected_ids[]: 选中的题目ID数组
```

**响应:** 重定向到题目列表

---

### 2.9 AJAX创建科目

| 项目 | 内容 |
|------|------|
| **URL** | `/question/subjects/ajax_create/` |
| **方法** | `POST` |
| **功能** | 通过AJAX创建新科目 |
| **认证** | 管理员权限 |

**请求体 (JSON):**
```json
{
    "name": "科目名称"
}
```

**响应 (JSON):**
```json
{
    "id": 1,
    "name": "科目名称"
}
```

---

### 2.10 AJAX创建题型

| 项目 | 内容 |
|------|------|
| **URL** | `/question/problem_types/ajax_create/` |
| **方法** | `POST` |
| **功能** | 通过AJAX创建新题型 |
| **认证** | 管理员权限 |

**请求体 (JSON):**
```json
{
    "name": "题型名称"
}
```

**响应 (JSON):**
```json
{
    "id": 1,
    "name": "题型名称"
}
```

---

### 2.11 知识点列表

| 项目 | 内容 |
|------|------|
| **URL** | `/question/knowledge-points/` |
| **方法** | `GET` |
| **功能** | 知识点列表管理 |
| **认证** | 管理员权限 |

**请求参数 (Query):**
```
q: 搜索关键词
```

**响应:** 渲染知识点列表HTML页面

---

### 2.12 创建知识点

| 项目 | 内容 |
|------|------|
| **URL** | `/question/knowledge-points/create/` |
| **方法** | `GET`, `POST` |
| **功能** | 创建新知识点 |
| **认证** | 管理员权限 |

**请求参数 (POST):**
```
name: 知识点名称
subject: 所属科目
description: 描述
```

---

### 2.13 更新知识点

| 项目 | 内容 |
|------|------|
| **URL** | `/question/knowledge-points/update/<int:kp_id>/` |
| **方法** | `GET`, `POST` |
| **功能** | 编辑知识点 |
| **认证** | 管理员权限 |

**路径参数:**
```
kp_id: 知识点ID
```

---

### 2.14 删除知识点

| 项目 | 内容 |
|------|------|
| **URL** | `/question/knowledge-points/delete/<int:kp_id>/` |
| **方法** | `POST` |
| **功能** | 删除知识点 |
| **认证** | 管理员权限 |

**路径参数:**
```
kp_id: 知识点ID
```

---

### 2.15 获取题目元数据 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/question/wx/get_problem_meta_data/` |
| **方法** | `GET` |
| **功能** | 获取创建题目所需的下拉选项数据 |

**响应 (JSON):**
```json
{
    "success": true,
    "data": {
        "problemTypes": [
            {"id": 1, "name": "选择题"},
            {"id": 2, "name": "填空题"}
        ],
        "subjects": [
            {"id": 1, "name": "数学"}
        ],
        "tags": [...],
        "knowledgePoints": [...]
    }
}
```

---

### 2.16 随机获取题目 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/question/wx/detail/random/` |
| **方法** | `GET` |
| **功能** | 随机获取一道激活状态的题目 |
| **认证** | JWT认证 |

**响应 (JSON):**
```json
{
    "question": {
        "id": 1,
        "content": "题目内容",
        "problem_type": "选择题",
        "difficulty": 3
    }
}
```

---

### 2.17 搜索题目 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/question/wx/search/` |
| **方法** | `GET` |
| **功能** | 搜索题目，支持关键词和知识点筛选 |
| **认证** | JWT认证 |

**请求参数 (Query):**
```
keyword: 搜索关键词
kp_id: 知识点ID
```

**响应 (JSON):**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "title": "题目标题",
            "content": "题目内容"
        }
    ],
    "total": 100
}
```

---

### 2.18 获取指定题目详情 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/question/wx/detail/<int:question_id>/` |
| **方法** | `GET` |
| **功能** | 获取指定ID的题目详情 |
| **认证** | JWT认证 |

**路径参数:**
```
question_id: 题目ID
```

**响应 (JSON):**
```json
{
    "success": true,
    "question": {
        "id": 1,
        "content": "题目内容",
        "answer": "答案",
        "analysis": "解析",
        "difficulty": 3,
        "knowledge_points": ["知识点1", "知识点2"]
    }
}
```

---

### 2.19 获取学生学习统计 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/question/wx/student/stats/` |
| **方法** | `GET` |
| **功能** | 获取学生的学习统计数据和能力画像 |
| **认证** | JWT认证 |

**响应 (JSON):**
```json
{
    "success": true,
    "data": {
        "total_questions": 50,
        "avg_mastery": 3.5,
        "stats_list": [
            {
                "knowledge_point": "函数",
                "mastery_level": 4,
                "practice_count": 20
            }
        ]
    }
}
```

---

## 3. 批改模块 (gradingModule)

### 3.1 提交作业 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/grading/wx/submit/` |
| **方法** | `GET`, `POST` |
| **功能** | 学生提交作业答案，POST创建新提交并触发异步批改 |
| **认证** | JWT认证 |

**请求体 (POST JSON/multipart):**
```json
{
    "questionId": 1,
    "userId": 1,
    "submitted_text": "提交的文本答案",
    "selectedAnswer": "A"
}
```
或上传文件:
```
submitted_image: 图片文件
```

**响应 (POST JSON):**
```json
{
    "id": 1,
    "message": "提交成功，正在判题中...",
    "status": "PENDING"
}
```

**响应 (GET):** 提交历史列表

---

### 3.2 提交记录列表 (网页端)

| 项目 | 内容 |
|------|------|
| **URL** | `/grading/submissions/` |
| **方法** | `GET` |
| **功能** | 显示所有提交记录列表，支持筛选 |
| **认证** | 管理员权限 |

**请求参数 (Query):**
```
status: 状态筛选
assignment: 作业ID
student: 学生ID
page: 页码
```

**响应:** 渲染提交列表HTML页面

---

### 3.3 提交详情 (网页端)

| 项目 | 内容 |
|------|------|
| **URL** | `/grading/submissions/<int:submission_id>/` |
| **方法** | `GET` |
| **功能** | 查看提交详情 |
| **认证** | 管理员权限 |

**路径参数:**
```
submission_id: 提交ID
```

**响应:** 渲染提交详情HTML页面

---

### 3.4 重新批改

| 项目 | 内容 |
|------|------|
| **URL** | `/grading/submission/<int:submission_id>/regrade/` |
| **方法** | `POST` |
| **功能** | 重新批改作业 |
| **认证** | 管理员权限 |

**路径参数:**
```
submission_id: 提交ID
```

**响应:** 重定向到提交列表

---

### 3.5 获取提交图片

| 项目 | 内容 |
|------|------|
| **URL** | `/grading/submission-image/<int:submission_id>/` |
| **方法** | `GET` |
| **功能** | 获取提交的图片 |

**路径参数:**
```
submission_id: 提交ID
```

**响应:** 图片二进制数据

---

### 3.6 获取我的提交记录 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/grading/wx/submissions/` |
| **方法** | `GET` |
| **功能** | 获取当前用户的提交记录，支持分页、排序、筛选 |
| **认证** | JWT认证 |

**请求参数 (Query):**
```
page: 页码
limit: 每页数量
offset: 偏移量
sort_by: 排序字段
filter_by: 筛选条件
user_id: 用户ID
```

**响应 (JSON):**
```json
{
    "data": [
        {
            "id": 1,
            "problem_title": "题目标题",
            "status": "GRADED",
            "score": 85,
            "submitted_time": "2024-01-01 10:00:00"
        }
    ],
    "total_count": 100,
    "page": 1,
    "limit": 20,
    "has_more": true
}
```

---

### 3.7 获取单条提交详情 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/grading/wx/submissions/<int:submission_id>/` |
| **方法** | `GET` |
| **功能** | 获取单条提交的详细信息 |
| **认证** | JWT认证 |

**路径参数:**
```
submission_id: 提交ID
```

**响应 (JSON):**
```json
{
    "problem_title": "题目标题",
    "submitted_time": "2024-01-01 10:00:00",
    "status": "GRADED",
    "score": 85,
    "feedback": "批改反馈",
    "submitted_text": "提交内容",
    "answer": "正确答案",
    "analysis": "解析"
}
```

---

### 3.8 批量操作提交记录

| 项目 | 内容 |
|------|------|
| **URL** | `/grading/submissions/batch-action/` |
| **方法** | `POST` |
| **功能** | 批量重新批改或删除提交记录 |
| **认证** | 管理员权限 |

**请求参数 (POST):**
```
action: regrade/delete
selected_ids[]: 选中的提交ID数组
```

**响应:** 重定向到提交列表

---

### 3.9 根据作业ID获取提交记录

| 项目 | 内容 |
|------|------|
| **URL** | `/grading/wx/submissions/assignment_id=<int:assignment_id>/` |
| **方法** | `GET` |
| **功能** | 获取指定作业的所有提交记录 |

**路径参数:**
```
assignment_id: 作业ID
```

**响应 (JSON):**
```json
[
    {
        "record_id": 1,
        "problem_title": "题目标题",
        "student_name": "学生姓名",
        "status": "GRADED",
        "score": 85
    }
]
```

---

## 4. 作业与班级模块 (assignmentAndClassModule)

### 4.1 获取题目元数据 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/assignment/wx/get_problem_meta_data/` |
| **方法** | `GET` |
| **功能** | 获取创建题目所需的元数据 |

**响应 (JSON):**
```json
{
    "success": true,
    "data": {
        "problemTypes": [...],
        "subjects": [...],
        "tags": [...],
        "knowledgePoints": [...]
    }
}
```

---

### 4.2 发布作业 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/assignment/wx/push_assignment/` |
| **方法** | `POST` |
| **功能** | 教师发布新作业，同时创建题目并关联班级 |
| **认证** | JWT认证 + 教师权限 |

**请求体 (JSON):**
```json
{
    "class_id": 1,
    "title": "作业标题",
    "description": "作业描述",
    "deadline": "2024-12-31 23:59:59",
    "content": "题目内容",
    "problem_type": 1,
    "subject": 1,
    "difficulty": 3,
    "knowledge_points": [1, 2, 3],
    "points": 10,
    "answer": "正确答案",
    "explanation": "答案解析"
}
```

**响应 (JSON):**
```json
{
    "success": true,
    "assignment_id": 1,
    "problem_id": 1,
    "message": "作业发布成功"
}
```

---

### 4.3 获取学生作业列表 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/assignment/wx/show_assignment/` |
| **方法** | `GET` |
| **功能** | 学生获取自己的作业列表 |
| **认证** | JWT认证 |

**请求头:**
```
ClassId: 班级ID (可选，用于筛选特定班级)
```

**响应 (JSON):**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "title": "作业标题",
            "deadline": "2024-12-31 23:59:59",
            "status": "PENDING",
            "score": null
        }
    ]
}
```

---

### 4.4 获取作业详情 (微信-学生)

| 项目 | 内容 |
|------|------|
| **URL** | `/assignment/wx/get_student_homework_detail/<int:assignment_id>/` |
| **方法** | `GET` |
| **功能** | 学生获取单份作业的详细内容 |
| **认证** | JWT认证 |

**路径参数:**
```
assignment_id: 作业ID
```

**响应 (JSON):**
```json
{
    "data": {
        "assignment_id": 1,
        "assignment_title": "作业标题",
        "problem_content": "题目内容",
        "deadline": "2024-12-31 23:59:59",
        "description": "作业描述",
        "status": "PENDING"
    }
}
```

---

### 4.5 教师获取作业列表 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/assignment/wx/teacher_get_assignments/<int:class_id>` |
| **方法** | `GET` |
| **功能** | 教师获取指定班级的作业列表 |
| **认证** | JWT认证 |

**路径参数:**
```
class_id: 班级ID
```

**响应 (JSON):**
```json
{
    "data": [
        {
            "id": 1,
            "title": "作业标题",
            "deadline": "2024-12-31 23:59:59",
            "submission_count": 30,
            "total_count": 50
        }
    ]
}
```

---

### 4.6 教师获取作业统计详情 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/assignment/wx/teacher_get_assignments_detail/<int:class_id>/<int:assignment_id>/` |
| **方法** | `GET` |
| **功能** | 教师获取单个作业的统计信息 |
| **认证** | JWT认证 |

**路径参数:**
```
class_id: 班级ID
assignment_id: 作业ID
```

**响应 (JSON):**
```json
{
    "data": {
        "id": 1,
        "title": "作业标题",
        "totalCount": 50,
        "submittedCount": 30,
        "gradedCount": 25,
        "avgScore": 78.5,
        "deadline": "2024-12-31 23:59:59"
    }
}
```

---

### 4.7 教师获取学生提交列表 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/assignment/wx/teacher_get_students_assignments_list/<int:class_id>/<int:assignment_id>/` |
| **方法** | `GET` |
| **功能** | 教师获取某作业下所有学生的提交状态 |
| **认证** | JWT认证 |

**路径参数:**
```
class_id: 班级ID
assignment_id: 作业ID
```

**响应 (JSON):**
```json
{
    "data": [
        {
            "id": 1,
            "name": "学生姓名",
            "submitted": true,
            "status": "GRADED",
            "score": 85
        }
    ]
}
```

---

### 4.8 更新作业 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/assignment/wx/update_assignment/<int:assignment_id>/` |
| **方法** | `POST` |
| **功能** | 教师编辑/更新作业信息 |
| **认证** | JWT认证 (作业创建者) |

**路径参数:**
```
assignment_id: 作业ID
```

**请求体 (JSON):**
```json
{
    "title": "新标题",
    "description": "新描述",
    "deadline": "2024-12-31 23:59:59"
}
```

**响应 (JSON):**
```json
{
    "success": true,
    "message": "作业修改成功",
    "data": {...}
}
```

---

### 4.9 批量发布作业 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/assignment/wx/batch_push_assignments/` |
| **方法** | `POST` |
| **功能** | 从题库选题批量发布作业 |
| **认证** | JWT认证 + 教师权限 |

**请求体 (JSON):**
```json
{
    "class_id": 1,
    "deadline": "2024-12-31 23:59:59",
    "problems": [1, 2, 3],
    "title_prefix": "每日练习"
}
```

**响应 (JSON):**
```json
{
    "success": true,
    "message": "成功发布 3 个作业",
    "count": 3
}
```

---

### 4.10 作业列表 (网页端)

| 项目 | 内容 |
|------|------|
| **URL** | `/assignment/assignment_list/` |
| **方法** | `GET` |
| **功能** | 后台管理 - 作业列表 |
| **认证** | 管理员权限 |

**请求参数 (Query):**
```
search_query: 搜索关键词
class_filter: 班级筛选
teacher_filter: 教师筛选
status_filter: 状态筛选
page: 页码
```

**响应:** 渲染作业列表HTML页面

---

### 4.11 作业详情 (网页端)

| 项目 | 内容 |
|------|------|
| **URL** | `/assignment/assignment_detail/<int:assignment_id>/` |
| **方法** | `GET` |
| **功能** | 后台管理 - 作业详情，包含学生提交统计 |
| **认证** | 管理员权限 |

**路径参数:**
```
assignment_id: 作业ID
```

**响应:** 渲染作业详情HTML页面

---

## 5. BKT模块 (BKTModule)

### 5.1 学生知识画像 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/wx/student/<int:student_id>/profile/` |
| **方法** | `GET` |
| **功能** | 获取学生的知识掌握画像，支持智能刷新控制 |
| **认证** | JWT认证 |

**路径参数:**
```
student_id: 学生ID
```

**请求参数 (Query):**
```
refresh: true/false - 是否强制刷新 (学生30分钟内只能刷新一次)
```

**响应 (JSON):**
```json
{
    "success": true,
    "data": {
        "knowledge_profile": [
            {
                "knowledge_point_id": 1,
                "knowledge_point_name": "函数",
                "mastery_probability": 0.85,
                "practice_count": 20
            }
        ],
        "overall_mastery": 0.75,
        "strengths": ["函数", "方程"],
        "weaknesses": ["几何"]
    },
    "refreshed": false,
    "time_left": 1800
}
```

---

### 5.2 预测学生表现 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/wx/student/<int:student_id>/prediction/` |
| **方法** | `POST` |
| **功能** | 预测学生在指定知识点上的表现 |
| **认证** | JWT认证 |

**路径参数:**
```
student_id: 学生ID
```

**请求体 (JSON):**
```json
{
    "knowledge_point_ids": [1, 2, 3]
}
```

**响应 (JSON):**
```json
{
    "success": true,
    "data": {
        "predictions": [
            {
                "knowledge_point_id": 1,
                "correct_probability": 0.85
            }
        ]
    }
}
```

---

### 5.3 班级知识分析 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/wx/class/<str:class_id>/analytics/` |
| **方法** | `GET` |
| **功能** | 获取班级知识点掌握分析 |
| **认证** | JWT认证 + 教师权限 (user_attribute >= 2) |

**路径参数:**
```
class_id: 班级ID
```

**响应 (JSON):**
```json
{
    "success": true,
    "data": [
        {
            "knowledge_point_id": 1,
            "knowledge_point_name": "函数",
            "average_mastery": 0.75,
            "student_count": 50,
            "high_mastery_count": 30,
            "low_mastery_count": 5
        }
    ]
}
```

---

### 5.4 处理学习事件 (微信)

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/wx/process-learning-event/` |
| **方法** | `POST` |
| **功能** | 内部API - 处理学习事件，更新BKT模型状态 |

**请求体 (JSON):**
```json
{
    "student_id": 1,
    "knowledge_point_id": 1,
    "is_correct": true,
    "submission_id": 1
}
```

**响应 (JSON):**
```json
{
    "success": true,
    "data": {
        "mastery_probability": 0.8,
        "probability_change": 0.1,
        "improvement": true
    }
}
```

---

### 5.5 学生知识画像 (管理系统)

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/student/<int:student_id>/profile/` |
| **方法** | `GET` |
| **功能** | 管理系统获取学生知识画像 |
| **认证** | Session登录认证 |

**路径参数:**
```
student_id: 学生ID
```

**请求参数 (Query):**
```
refresh: true/false
```

---

### 5.6 预测学生表现 (管理系统)

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/student/<int:student_id>/prediction/` |
| **方法** | `POST` |
| **功能** | 管理系统预测学生表现 |
| **认证** | Session登录认证 |

---

### 5.7 班级知识分析 (管理系统)

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/class/<str:class_id>/analytics/` |
| **方法** | `GET` |
| **功能** | 管理系统获取班级知识分析 |
| **认证** | Session登录认证 + 教师权限 |

---

### 5.8 知识点BKT参数

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/knowledge-point/<int:kp_id>/parameters/` |
| **方法** | `GET` |
| **功能** | 获取知识点的BKT模型参数 |
| **认证** | Session登录认证 + 管理员权限 |

**路径参数:**
```
kp_id: 知识点ID
```

**响应 (JSON):**
```json
{
    "success": true,
    "data": {
        "knowledge_point": {
            "id": 1,
            "name": "函数"
        },
        "bkt_parameters": {
            "p_init": 0.2,
            "p_learn": 0.1,
            "p_forget": 0.1,
            "p_guess": 0.25,
            "p_slip": 0.3
        },
        "training_samples": 100,
        "last_trained": "2024-01-01 10:00:00"
    }
}
```

---

### 5.9 处理学习事件 (管理系统)

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/process-learning-event/` |
| **方法** | `POST` |
| **功能** | 内部API - 处理学习事件 |
| **认证** | Session登录认证 |

**请求体 (JSON):**
```json
{
    "student_id": 1,
    "knowledge_point_id": 1,
    "is_correct": true,
    "submission_id": 1
}
```

---

### 5.10 BKT数据迁移

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/migrate-data/` |
| **方法** | `POST` |
| **功能** | 执行BKT数据迁移 |
| **认证** | Session登录认证 + 管理员权限 |

**请求体 (JSON):**
```json
{
    "type": "full"
}
```

**type可选值:**
- `full`: 完整迁移
- `knowledge_points`: 仅知识点
- `submissions`: 仅提交记录
- `parameters`: 仅参数

**响应 (JSON):**
```json
{
    "success": true,
    "data": {
        "migrated_count": 1000,
        "errors": []
    }
}
```

---

### 5.11 学生仪表板页面

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/student/dashboard/` |
| **方法** | `GET` |
| **功能** | BKT学生知识追踪仪表板页面 |
| **认证** | 需要登录 |

**响应:** 渲染HTML页面

---

### 5.12 班级仪表板页面

| 项目 | 内容 |
|------|------|
| **URL** | `/bkt/class/dashboard/` |
| **方法** | `GET` |
| **功能** | BKT班级分析仪表板页面 |
| **认证** | 需要登录 + 教师权限 |

**响应:** 渲染HTML页面

---

## 6. DKT模块 (dkt_app)

### 6.1 获取学生掌握度预测 API

| 项目 | 内容 |
|------|------|
| **URL** | `/dkt/mastery/<int:student_id>/` |
| **方法** | `GET` |
| **功能** | 获取特定学生的DKT知识掌握度预测 |

**路径参数:**
```
student_id: 学生ID
```

**响应 (JSON):**
```json
{
    "student_id": 1,
    "student_name": "张三",
    "knowledge_dim": 50,
    "mastery_predictions": [
        {
            "knowledge_point_id": 1,
            "mastery_probability": 0.85
        }
    ],
    "exercise_sequence": [1, 2, 3],
    "concept_labels": ["函数", "方程"]
}
```

---

### 6.2 我的掌握度页面

| 项目 | 内容 |
|------|------|
| **URL** | `/dkt/my_mastery/` |
| **方法** | `GET` |
| **功能** | 显示当前登录用户的DKT知识掌握度预测页面 |
| **认证** | 需要登录 |

**响应:**
- 学生: 渲染掌握度页面
- 教师/管理员: 重定向到学生列表

---

### 6.3 查看学生掌握度

| 项目 | 内容 |
|------|------|
| **URL** | `/dkt/student/<int:student_id>/mastery/` |
| **方法** | `GET` |
| **功能** | 教师/管理员查看特定学生的学习情况 |
| **认证** | 需要登录 + 教师/管理员权限 |

**路径参数:**
```
student_id: 学生ID
```

**响应:** 渲染学生掌握度页面

---

## 7. 核心模块 (IntelligentHomeworkGradingSystem)

### 7.1 系统首页仪表盘

| 项目 | 内容 |
|------|------|
| **URL** | `/` |
| **方法** | `GET` |
| **功能** | 系统首页仪表盘，显示统计信息 |
| **认证** | 需要登录 |

**响应:** 渲染dashboard.html页面

---

### 7.2 管理后台

| 项目 | 内容 |
|------|------|
| **URL** | `/admin/` |
| **方法** | `GET`, `POST` |
| **功能** | Django Admin管理后台 |
| **认证** | 管理员权限 (is_staff=True) |

**响应:** Django Admin界面

---

## 附录：HTTP状态码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 302 | 重定向 |
| 400 | 请求参数错误 |
| 401 | 未认证/认证失败 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 附录：提交状态说明

| 状态 | 说明 |
|------|------|
| PENDING | 待批改 |
| GRADING | 批改中 |
| GRADED | 已批改 |
| FAILED | 批改失败 |

---

## 附录：文件路径汇总

| 模块 | URL文件路径 | Views文件路径 |
|------|-------------|---------------|
| 主路由 | `IntelligentHomeworkGradingSystem/urls.py` | `IntelligentHomeworkGradingSystem/views.py` |
| 用户管理 | `userManageModule/urls.py` | `userManageModule/views.py`, `userManageModule/class_views.py` |
| 题目管理 | `questionManageModule/urls.py` | `questionManageModule/views.py` |
| 批改模块 | `gradingModule/urls.py` | `gradingModule/views.py` |
| 作业班级 | `assignmentAndClassModule/urls.py` | `assignmentAndClassModule/views.py` |
| BKT模块 | `BKTModule/urls.py` | `BKTModule/views.py` |
| DKT模块 | `dkt_app/urls.py` | `dkt_app/views.py` |
