# 前端设计与风格指南

## 1. 概述
本文档概述了智能作业评分系统前端的设计规范。目标是确保所有页面具有一致、现代且用户友好的界面。

## 2. 技术栈
- **框架:** Django Templates
- **CSS 框架:** Bootstrap 5.3.3
- **图标:** Font Awesome 6.5.2 (首选) / Bootstrap Icons
- **JS:** Vanilla JS / Bootstrap Bundle (包含 Popper.js)

## 3. 视觉风格指南

### 3.1. 配色方案
- **主色 (Primary Color):** `#0d6efd` (Bootstrap Primary Blue) - 用于主要操作、激活状态和关键高亮。
- **次要色 (Secondary Color):** `#6c757d` (Bootstrap Secondary Gray) - 用于次要操作、边框和柔和文本。
- **成功色 (Success Color):** `#198754` (Bootstrap Success Green) - 用于完成、成功消息和积极状态。
- **危险色 (Danger Color):** `#dc3545` (Bootstrap Danger Red) - 用于删除操作、错误和严重警告。
- **警告色 (Warning Color):** `#ffc107` (Bootstrap Warning Yellow) - 用于警报和待处理状态。
- **信息色 (Info Color):** `#0dcaf0` (Bootstrap Info Cyan) - 用于信息性消息。
- **背景色 (Background Color):** `#f8f9fa` (Bootstrap Light) - 全局页面背景。
- **卡片背景 (Card Background):** `#ffffff` (White) - 内容容器。

### 3.2. 排版
- **字体家族:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif` (系统 UI 栈)。
- **标题:**
  - H1/H2: 页面标题、章节标题 (字重: 600/700)。
  - H3-H6: 子章节、卡片标题。
- **正文:** 标准 Bootstrap 默认值 (1rem 基准大小)。

### 3.3. 布局与间距
- **容器:** 使用 `.container` 或 `.container-fluid` 包裹页面。
- **间距:** 使用 Bootstrap 工具类 (`m-*`, `p-*`, `my-4`, `mb-3` 等)。主要章节之间的标准垂直间距为 `my-4`。
- **卡片:** 使用带 `.shadow-sm` 的 `.card` 进行内容分组。使用阴影时移除默认边框 (`border: 0`) 以获得更整洁的外观。

### 3.4. 组件

#### 按钮
- **主要操作:** `.btn-primary` (例如：保存、提交、创建)。
- **次要操作:** `.btn-secondary` 或 `.btn-outline-secondary` (例如：取消、返回)。
- **破坏性操作:** `.btn-danger` (例如：删除)。
- **图标按钮:** 在按钮内使用 Font Awesome 图标 (例如：`<i class="fas fa-plus me-2"></i>新建`)。

#### 表格
- **样式:** `.table .table-hover .table-striped`。
- **表头:** `.table-light` 或 `.table-dark` 用于对比。
- **垂直对齐:** `.align-middle` 用于表格行。
- **操作:** 将操作按钮分组在 `.btn-group` 中或使用间距分隔。

#### 表单
- **控件:** 使用标准 Bootstrap `.form-control`, `.form-select`, `.form-check`。
- **布局:** 在表单内使用 `.row` 和 `.col-*` 进行网格布局。
- **标签:** `.form-label`。

#### 导航
- **导航栏:** `.navbar-dark .bg-dark` 配合 `.shadow-sm`。
- **激活状态:** 高亮导航栏中的当前页面。

## 4. 交互指南

- **悬停效果:** 按钮和链接应有清晰的悬停状态 (由 Bootstrap 处理)。
- **反馈:**
  - **成功:** 操作成功后显示绿色警报或 Toast 消息。
  - **错误:** 失败时显示红色警报。
  - **加载中:** 适用时对异步操作使用加载指示器 (`.spinner-border`)。
  - **确认:** 对破坏性操作 (删除) 使用 `confirm()` 或模态框。

## 5. 新功能实现清单
1.  **继承基类:** 始终继承 `page_base.html` (或 `backend_sys_base_page.html`)。
2.  **使用区块:** 内容放在 `{% block content %}` 中。
3.  **响应式:** 确保布局在移动设备上正常显示 (使用 `.col-md-*`, `.d-none` 等)。
4.  **一致性:** 列表视图复制 `question_list.html` 或 `submission_list.html` 的结构。
