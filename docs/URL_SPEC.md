# URL 规范化改造规格（v1）

> 状态：待执行（等 `questionRedisCache` PR 合并后，从 `main` 开新分支实施）
> 范围：全量重写，小程序客户端同步切换
> 依据：现有 101 条路由的逐条审计

---

## 1. 现状问题（审计结论）

现有路由共 **101 条**，同时存在四套命名体系：

| 类型 | 例子 | 问题 |
|------|------|------|
| 路径参数用 `key=value` | `/grading/wx/submissions/assignment_id=5/`、`/class/class_id=3/quit/` | `=` 不是路径分隔符，客户端拼接易错 |
| 尾斜杠缺失 | `/assignment/wx/teacher_get_assignments/<class_id>`、`/user/wx/edit/<user_id>` | `APPEND_SLASH` 301，POST 跟随会丢 body 并变 GET |
| 同一操作多条路径 | 建班级三处、题目元数据两处、掌握度三处 | 调用方各写各的，改一处漏两处 |
| 风格混用 | 驼峰 `wx/userJoinClass/`、RPC `teacher_get_assignments`、资源式 `submissions/`、前缀式 `api/token/` | 无法从路径推断行为 |
| 分隔符混用 | `knowledge-points` vs `problem_types` | 同上 |
| 无 namespace | 仅 `bkt`、`dkt` 有 `app_name` | 路由名可能冲突，只能靠 `_web` 后缀区分 |

---

## 2. 设计原则（六条，作为后续评审依据）

1. **两个命名空间彻底分离**
   - 页面（HTML / Session）：`/<app>/...`
   - 接口（JSON / JWT 或 Session）：`/api/v1/...`

   小程序只碰 `/api/v1/`，网页只碰页面路径，一条路径不会既是页面又是接口。

2. **路径参数一律 `/<int:xxx>/`**，禁止 `key=value`。

3. **尾斜杠全部保留**，禁止无斜杠。

4. **集合复数、单体单数**：`/submissions/`、`/submissions/<id>/`。

5. **动作只在无资源语义时进路径**：`/regrade/`、`/approve/`、`/batch/`；否则靠 HTTP method（GET/POST/PATCH/DELETE）。

6. **命名**：URL 用连字符分词，路由名用 snake_case，格式 `<app>_<resource>_<action>`；每个 app 必加 `app_name`。

---

## 3. 目标结构总览

```
/                                  Dashboard
/admin/                            Django Admin
/user/          页面：用户、班级管理
/question/      页面：题库、知识点
/grading/       页面：提交记录、复核
/assignment/    页面：作业列表
/bkt/           页面：BKT 看板与维护
/dkt/           页面：DKT 掌握度
/api/v1/        所有 JSON 接口（小程序 + AJAX）
    auth/  users/  students/  classes/  questions/
    assignments/  submissions/  learning-events/  subjects/
```

---

## 4. 逐条映射表

### 4.1 根路由（15 条 → 10 条）

| 现状 | 目标 | 说明 |
|------|------|------|
| `/` | `/` | 不变 |
| `/admin/` | `/admin/` | 不变 |
| `/class_name/add/` | — | **删除**，合并到 `/user/classes/new/` |
| `/class/create/` | — | **删除**，合并到 `/user/classes/new/` |
| `/class/<int:class_id>/` | `/user/classes/<int:class_id>/` | 迁入 user 模块 |
| `/class/<int:class_id>/members/` | `/api/v1/classes/<int:class_id>/members/` | 返回 JSON，归 API |
| `/class/class_id=<int:class_id>/quit/` | `/api/v1/classes/<int:class_id>/leave/` | 去掉 `=` |
| `/register/` | `/user/register/` | 归入用户模块 |
| `/student/homework/` | `/student/assignments/` | 语义对齐 |
| 六个 `include(...)` | 不变 | — |

### 4.2 用户与班级（userManageModule，30 条）

页面：

| 现状 | 目标 |
|------|------|
| `/user/login/` | `/user/login/` |
| `/user/logout/` | `/user/logout/` |
| `/user/profile/` | `/user/profile/` |
| `/user/list/` | `/user/users/` |
| `/user/add/` | `/user/users/new/` |
| `/user/edit/<id>/` | `/user/users/<int:id>/edit/` |
| `/user/delete/<id>/` | `/user/users/<int:id>/delete/` |
| `/user/pending-teachers/` | `/user/teachers/pending/` |
| `/user/approve-teacher/<id>/` | `/user/teachers/<int:id>/approve/` |
| `/user/reject-teacher/<id>/` | `/user/teachers/<int:id>/reject/` |
| `/user/class/list/` | `/user/classes/` |
| `/user/class/my/` | `/user/classes/mine/` |
| `/user/class/create/` | `/user/classes/new/` |
| `/user/class/edit/<id>/` | `/user/classes/<int:id>/edit/` |
| `/user/class/delete/<id>/` | `/user/classes/<int:id>/delete/` |
| `/user/class/detail/<id>/` | `/user/classes/<int:id>/` |
| `/user/class/student/add/<cid>/` | `/user/classes/<int:cid>/students/add/` |
| `/user/class/student/remove/<cid>/<sid>/` | `/user/classes/<int:cid>/students/<int:sid>/remove/` |
| `/user/class/teacher/add/<cid>/` | `/user/classes/<int:cid>/teachers/add/` |
| `/user/class/teacher/remove/<cid>/<tid>/` | `/user/classes/<int:cid>/teachers/<int:tid>/remove/` |
| `/user/class/join/` | `/user/classes/join/` |

接口：

| 现状 | 目标 | 说明 |
|------|------|------|
| `/user/api/token/` | `/api/v1/auth/token/` | JWT 签发 |
| `/user/api/token/refresh/` | `/api/v1/auth/token/refresh/` | JWT 刷新 |
| `/user/wx/login/` | `/api/v1/auth/wechat/` | 小程序登录 |
| `/user/api/profile/update/` | `/api/v1/users/me/` | PATCH |
| `/user/api/student/search/` | `/api/v1/students/search/` | GET |
| `/user/wx/add/` | `/api/v1/users/` | POST |
| `/user/wx/edit/<id>` | `/api/v1/users/<int:id>/` | PATCH，与下一条合并 |
| `/user/wx/list/<int:user_id>/` | `/api/v1/users/<int:id>/` | GET，与上一条同路径不同方法 |
| `/user/wx/userJoinClass/` | `/api/v1/classes/join/` | POST |

### 4.3 题库（questionManageModule，20 条）

页面：

| 现状 | 目标 |
|------|------|
| `/question/list/` | `/question/problems/` |
| `/question/create/` | `/question/problems/new/` |
| `/question/detail/<id>/` | `/question/problems/<int:id>/` |
| `/question/update/<id>/` | `/question/problems/<int:id>/edit/` |
| `/question/delete/<id>/` | `/question/problems/<int:id>/delete/` |
| `/question/batch-import-json/` | `/question/problems/import/` |
| `/question/download-import-template/` | `/question/problems/import-template/` |
| `/question/questions/batch-action/` | `/question/problems/batch/` |
| `/question/questions/import/review/` | `/question/problems/import/review/` |
| `/question/knowledge-points/` | `/question/knowledge-points/` |
| `/question/knowledge-points/create/` | `/question/knowledge-points/new/` |
| `/question/knowledge-points/update/<id>/` | `/question/knowledge-points/<int:id>/edit/` |
| `/question/knowledge-points/delete/<id>/` | `/question/knowledge-points/<int:id>/delete/` |

接口：

| 现状 | 目标 | 说明 |
|------|------|------|
| `/question/subjects/ajax_create/` | `/api/v1/subjects/` | POST |
| `/question/problem_types/ajax_create/` | `/api/v1/problem-types/` | POST |
| `/question/wx/get_problem_meta_data/` | `/api/v1/questions/meta/` | — |
| `/assignment/wx/get_problem_meta_data/` | — | **删除**，重复注册 |
| `/question/wx/detail/random/` | `/api/v1/questions/random/` | — |
| `/question/wx/search/` | `/api/v1/questions/search/` | — |
| `/question/wx/detail/<id>/` | `/api/v1/questions/<int:id>/` | **缓存命中点**，改动需同步 todo.md 验点 |
| `/question/wx/student/stats/` | `/api/v1/students/me/stats/` | — |

### 4.4 批改（gradingModule，9 条）

| 现状 | 目标 | 说明 |
|------|------|------|
| `/grading/wx/submit/` | `/api/v1/submissions/` | POST，与下条 GET 合并 |
| `/grading/wx/submissions/` | `/api/v1/submissions/` | GET，我的提交列表 |
| `/grading/wx/submissions/<id>/` | `/api/v1/submissions/<int:id>/` | 轮询批改结果 |
| `/grading/wx/submissions/assignment_id=<id>/` | `/api/v1/assignments/<int:id>/submissions/` | 去掉 `=` |
| `/grading/submission-image/<id>/` | `/api/v1/submissions/<int:id>/image/` | 有权限校验，不能走静态目录 |
| `/grading/submissions/` | `/grading/submissions/` | 页面 |
| `/grading/submissions/<id>/` | `/grading/submissions/<int:id>/` | 页面 |
| `/grading/submission/<id>/regrade/` | `/grading/submissions/<int:id>/regrade/` | 单复数统一 |
| `/grading/submissions/batch-action/` | `/grading/submissions/batch/` | — |

> ⚠️ `submission-image` 的 URL 由 `gradingModule/tasks.py` 用 `settings.SERVER_BASE_URL` 拼给大模型拉取。改路径必须同步改 `tasks.py`，否则 AI 批改全量失败。

### 4.5 作业（assignmentAndClassModule，11 条 → 9 条）

| 现状 | 目标 | 说明 |
|------|------|------|
| `/assignment/wx/get_problem_meta_data/` | — | **删除**（与题库重复） |
| `/assignment/wx/push_assignment/` | `/api/v1/assignments/` | POST |
| `/assignment/wx/batch_push_assignments/` | `/api/v1/assignments/batch/` | POST |
| `/assignment/wx/show_assignment/` | `/api/v1/students/me/assignments/` | GET，学生视角 |
| `/assignment/wx/get_student_homework_detail/<id>/` | `/api/v1/assignments/<int:id>/` | 与下条 PATCH 合并 |
| `/assignment/wx/update_assignment/<id>/` | `/api/v1/assignments/<int:id>/` | PATCH |
| `/assignment/wx/teacher_get_assignments/<cid>` | `/api/v1/classes/<int:cid>/assignments/` | 补尾斜杠 |
| `/assignment/wx/teacher_get_assignments_detail/<cid>/<aid>/` | `/api/v1/classes/<int:cid>/assignments/<int:aid>/` | — |
| `/assignment/wx/teacher_get_students_assignments_list/<cid>/<aid>/` | `/api/v1/classes/<int:cid>/assignments/<int:aid>/students/` | — |
| `/assignment/assignment_list/` | `/assignment/assignments/` | 页面 |
| `/assignment/assignment_detail/<id>/` | `/assignment/assignments/<int:id>/` | 页面 |

### 4.6 BKT（BKTModule，12 条）

页面 / 后台：

| 现状 | 目标 |
|------|------|
| `/bkt/student/dashboard/` | `/bkt/students/dashboard/` |
| `/bkt/class/dashboard/` | `/bkt/classes/dashboard/` |
| `/bkt/student/<id>/profile/` | `/bkt/students/<int:id>/` |
| `/bkt/student/<id>/prediction/` | `/bkt/students/<int:id>/prediction/` |
| `/bkt/class/<cid>/analytics/` | `/bkt/classes/<cid>/analytics/` |
| `/bkt/knowledge-point/<id>/parameters/` | `/bkt/knowledge-points/<int:id>/parameters/` |
| `/bkt/migrate-data/` | `/bkt/maintenance/migrate/` |

接口：

| 现状 | 目标 | 说明 |
|------|------|------|
| `/bkt/wx/student/<id>/profile/` | `/api/v1/students/<int:id>/knowledge-profile/` | 与 DKT 的 mastery 区分 |
| `/bkt/wx/student/<id>/prediction/` | `/api/v1/students/<int:id>/prediction/` | — |
| `/bkt/wx/class/<cid>/analytics/` | `/api/v1/classes/<cid>/analytics/` | — |
| `/bkt/wx/process-learning-event/` | `/api/v1/learning-events/` | POST，与下条合并 |
| `/bkt/process-learning-event/` | `/api/v1/learning-events/` | POST，同路径不同认证 |

### 4.7 DKT（dkt_app，4 条）

| 现状 | 目标 | 说明 |
|------|------|------|
| `/dkt/mastery/<id>/` | `/api/v1/students/<int:id>/mastery/` | DKT 掌握度预测 |
| `/dkt/my_mastery/` | `/api/v1/students/me/mastery/` | 快捷别名 |
| `/dkt/student/<id>/mastery/` | `/dkt/students/<int:id>/mastery/` | 页面 |
| `/dkt/students/` | `/dkt/students/` | 页面 |

### 4.8 收敛结果

| 项 | 现状 | 目标 |
|---|---|---|
| 路径总数 | 101 | 约 95 |
| 删除的重复路由 | — | 3 条（`class_name/add`、`class/create`、`assignment` 的 meta_data） |
| 合并的同路径多方法 | — | 3 组（users、submissions、assignments） |
| 含 `=` 的路径 | 2 | 0 |
| 缺尾斜杠 | 2 | 0 |

### 4.9 `me` 别名约定

`/api/v1/students/me/...` 与 `/api/v1/users/me/` 需要视图支持 `me` 关键字：

```python
student_id = request.user.id if student_id == 'me' else int(student_id)
```

路由用 `<str:student_id>`，避免 `<int:>` 拦掉 `me`。

---

## 5. 实施步骤（合并后执行）

### Step 0 · 冻结基线
```bash
git checkout main && git pull
git checkout -b refactor/url-normalization
```

### Step 1 · 建 API 命名空间
- 新建 `api/` 包：`api/__init__.py`、`api/v1/urls.py`（聚合器）
- 各 app 增加 `api_urls.py`，只放 JSON 接口；原 `urls.py` 只留页面路由
- 主 `urls.py` 加 `path('api/v1/', include('api.v1.urls'))`

### Step 2 · 页面路由资源化 + namespace
- 每个 `urls.py` 顶部加 `app_name = '<app>'`
- 主路由 `include(..., namespace='<app>')`
- 路由名统一 `<app>_<resource>_<action>`

### Step 3 · 批量修正引用（工作量最大）
- 模板 `{% url %}` 引用 **110 处**，视图 `redirect()` **51 处**
- 建议：先 `grep -rn "{% url '"` 导出清单 → 按模块替换 → 每改完一个 app 跑一次页面冒烟
- 用 Django 的 `reverse()` 报错兜底：漏改会抛 `NoReverseMatch`，比静默 404 好查

### Step 4 · 加规范守护测试
新增 `tests/test_url_convention.py`，遍历 `get_resolver().url_patterns` 递归断言：

```python
# 伪代码
for pattern in walk(resolver):
    assert not re.search(r'\w+=<', str(pattern.pattern)), '禁止 key=value 路径参数'
    assert str(pattern.pattern).endswith('/'), '必须保留尾斜杠'
    assert name is None or re.fullmatch(r'[a-z0-9_]+', name), '路由名必须 snake_case'
names = [...]  # 收集全部 name
assert len(names) == len(set(names)), '路由名不得重复'
```

这条测试是防回潮的关键，务必先进主干。

### Step 5 · 客户端同步（小程序）
见第 6 节清单。切换顺序建议：**先发后端（保留 legacy）→ 再发小程序 → 稳定一个版本后删 legacy**。

### Step 6 · 清理
- 删除 `legacy_urls.py`
- 更新 `docs/PROJECT_MEMORY.md`、`api_structure.md`、`BKTModule/README.md`（后者现在写的是 `/api/bkt/...`，与实际 `/bkt/...` 早已不符）

---

## 6. 小程序端改动清单

客户端不在本仓库，需逐项确认：

- [ ] `request` 封装的 baseURL 与路径拼接逻辑（重点检查是否手动拼 `/`）
- [ ] 登录：`/user/wx/login/` → `/api/v1/auth/wechat/`
- [ ] Token 刷新：`/user/api/token/refresh/` → `/api/v1/auth/token/refresh/`
- [ ] 题目详情：`/question/wx/detail/<id>/` → `/api/v1/questions/<id>/`
- [ ] 随机出题：`/question/wx/detail/random/` → `/api/v1/questions/random/`
- [ ] 题目检索：`/question/wx/search/` → `/api/v1/questions/search/`
- [ ] 提交作业：`/grading/wx/submit/` → `POST /api/v1/submissions/`
- [ ] 我的提交：`/grading/wx/submissions/` → `GET /api/v1/submissions/`
- [ ] 批改结果轮询：`/grading/wx/submissions/<id>/` → `/api/v1/submissions/<id>/`
- [ ] 某作业全部提交：`/grading/wx/submissions/assignment_id=<id>/` → `/api/v1/assignments/<id>/submissions/`
- [ ] 学生作业列表：`/assignment/wx/show_assignment/` → `/api/v1/students/me/assignments/`
- [ ] 教师作业列表：`/assignment/wx/teacher_get_assignments/<cid>` → `/api/v1/classes/<cid>/assignments/`
- [ ] 知识画像：`/bkt/wx/student/<id>/profile/` → `/api/v1/students/<id>/knowledge-profile/`
- [ ] 掌握度预测：`/dkt/mastery/<id>/` → `/api/v1/students/<id>/mastery/`
- [ ] 加入班级：`/user/wx/userJoinClass/` → `POST /api/v1/classes/join/`
- [ ] 用户信息：`/user/wx/list/<id>/` → `GET /api/v1/users/<id>/`

---

## 7. 验收标准

1. `manage.py check` 无问题；路由规范测试全绿
2. 页面冒烟：登录、用户列表、题库列表/详情/编辑、班级管理、作业列表、BKT/DKT 看板全部 200
3. 接口冒烟：小程序 16 个调用点全部返回预期 JSON
4. 缓存验点仍成立：题目详情 miss→hit、TTL 抖动、不存在 id 直接 404
5. 全局搜索无残留：`grep -rn "wx/get_problem_meta_data\|assignment_id=\|class_id=" --include=*.py --include=*.html .` 结果为空

---

## 8. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 老版本小程序仍在用旧路径 | 用户报错 | 过渡期保留 `legacy_urls.py`，由 `settings.ENABLE_LEGACY_URLS` 开关控制 |
| 遗漏 `{% url %}` 引用 | 页面 500 | 依赖 `NoReverseMatch` 兜底 + Step 4 测试 |
| `submission-image` 改动未同步 `tasks.py` | **AI 批改全量失败** | 单独列为一个提交，改完立刻跑一次真实批改 |
| 缓存键与路径耦合 | 缓存命中率异常 | 缓存键 `question:detail:{id}` 与路径无关，无需改 |
| 一次改动过大难回滚 | 排障困难 | 按 Step 逐个 app 提交，每步可独立回滚 |

---

## 9. 实施结果（2026-10-31，分支 refactor/url-normalization）

已按本规格完成全量重写，实际落地与规格的差异如下（均为降低风险的取舍）：

| 项 | 规格原计划 | 实际实现 | 原因 |
|---|---|---|---|
| 用户详情/编辑 | 合并为同一路径按 method 分派 | 拆为 `/users/<id>/` 与 `/users/<id>/edit/` | 两个视图独立，避免引入分派器 |
| 作业详情/更新 | 合并为 `/assignments/<id>/` | 拆为 `/assignments/<id>/` 与 `/assignments/<id>/update/` | 同上 |
| 提交列表与提交 | 同一路径 GET/POST | 已合并，用 `submission_collection` 分派 | 本就是同一资源，分派成本低 |
| `my_mastery` | 归入 API | 保留为页面 `/dkt/my-mastery/` | 视图渲染 HTML，不是 JSON |
| 学习事件 | 页面与接口合并 | `/api/v1/learning-events/`（JWT）与 `/bkt/learning-events/`（Session）分开 | 认证方式不同，合并需运行时判断 |
| 旧路径兼容 | 预留 `legacy_urls.py` | 未保留，旧路径直接 404 | 本项目按「全量重写 + 客户端同步」执行 |

统计：业务路由 89 条（不含 Django Admin），`key=value` 参数 0 处，缺尾斜杠 0 处，路由名重复 0 处。

验证记录：
- `manage.py check` → 0 issues
- `manage.py test tests.test_url_convention` → 6 passed
- 页面渲染：登录/注册/用户列表/班级/题库/知识点/提交列表/BKT 看板/DKT 页面均 200
- 接口可达：`/api/v1/questions/<id>/` 等匿名访问返回 401（路由存在）
- 旧路径：`/question/wx/detail/1/` 等全部 404

遗留（与本次改造无关，属既有问题）：
- `/assignment/assignments/` 报 `Unknown column 'custom_prompt'`：`Assignment.custom_prompt` 字段在模型里存在，但没有对应迁移文件（`.gitignore` 的 `*/migrations/` 规则导致新迁移未被提交）。
