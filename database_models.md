# 智能作业批改系统 - 数据库模型文档

## 目录
1. [模型概览](#模型概览)
2. [用户管理模块](#1-用户管理模块-usermanagemodule)
3. [题目管理模块](#2-题目管理模块-questionmanagemodule)
4. [批改模块](#3-批改模块-gradingmodule)
5. [作业管理模块](#4-作业管理模块-assignmentandclassmodule)
6. [BKT知识追踪模块](#5-bkt知识追踪模块-bktmodule)
7. [DKT深度知识追踪模块](#6-dkt深度知识追踪模块-dkt_app)
8. [模型关系图谱](#模型关系图谱)
9. [索引与约束](#索引与约束)

---

## 模型概览

| 模块 | 模型数量 | 主要模型 |
|------|----------|----------|
| userManageModule | 3 | User, className, ClassTeacher |
| questionManageModule | 9 | Problem, KnowledgePoint, StudentMastery |
| gradingModule | 1 | Submission |
| assignmentAndClassModule | 2 | Assignment, AssignmentStatus |
| BKTModule | 5 | BKTStudentState, BKTKnowledgeModel, LearningTrace |
| dkt_app | 2 | DKTModel, DKT (PyTorch神经网络) |

**总计**: 18个 Django ORM 模型 + 2个 PyTorch 神经网络模型

---

## 1. 用户管理模块 (userManageModule)

### 1.1 User (用户模型)

**功能描述**: 继承 Django AbstractUser 的自定义用户模型，支持用户认证、微信登录和班级关联。

**表名**: `auth_user` (Django默认)

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `uid` | CharField | max_length=6, unique, nullable, blank | 用户ID（用户可见），自动生成格式：年份后2位+4位随机数 |
| `phone` | BigIntegerField | nullable, blank, default=13500000000 | 手机号 |
| `gender` | SmallIntegerField | choices=[(1,'男'),(2,'女')], nullable, blank | 性别 |
| `user_attribute` | SmallIntegerField | choices=[(0,'未定义'),(1,'学生'),(2,'老师'),(3,'管理员'),(4,'超级管理员')], default=0 | 用户属性/角色 |
| `openid` | CharField | max_length=64, unique, nullable, blank | 微信OpenID |
| `unionid` | CharField | max_length=64, nullable, blank | 微信UnionID |
| `wx_nickName` | CharField | max_length=128, nullable, blank | 微信昵称 |
| `wx_avatar` | URLField | nullable, blank | 微信头像URL |
| `session_key` | CharField | max_length=128, nullable, blank | 微信会话密钥 |
| `wx_country` | CharField | max_length=30, nullable, blank | 国家 |
| `wx_province` | CharField | max_length=30, nullable, blank | 省份 |
| `wx_city` | CharField | max_length=30, nullable, blank | 城市 |
| `last_login_time` | DateTimeField | auto_now=True | 最后登录时间 |
| `class_in` | ManyToManyField | to=className, blank, related_name='members' | 所属班级（多对多） |

**继承字段** (来自 AbstractUser):

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `username` | CharField | 用户名 |
| `password` | CharField | 密码（加密存储） |
| `email` | EmailField | 邮箱 |
| `first_name` | CharField | 名 |
| `last_name` | CharField | 姓 |
| `is_staff` | BooleanField | 是否可登录Admin |
| `is_active` | BooleanField | 是否激活 |
| `is_superuser` | BooleanField | 是否超级管理员 |
| `date_joined` | DateTimeField | 注册时间 |
| `last_login` | DateTimeField | 最后登录时间 |

**模型方法**:

```python
def save(self, *args, **kwargs):
    """重写保存方法，确保用户有唯一的uid"""
    if not self.uid:
        self.uid = self.generate_unique_uid()
    super().save(*args, **kwargs)

def generate_unique_uid(self):
    """生成唯一用户ID，格式为年份后2位+4位随机数"""
    # 例如：240001, 249999
```

**用户属性值说明**:

| user_attribute | 角色 |
|----------------|------|
| 0 | 未定义 |
| 1 | 学生 |
| 2 | 老师 |
| 3 | 管理员 |
| 4 | 超级管理员 |

---

### 1.2 className (班级模型)

**功能描述**: 班级信息管理模型，包含班级基本信息和班主任关联。

**表名**: `userManageModule_classname`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `name` | CharField | max_length=100 | 班级名称 |
| `code` | CharField | max_length=6, unique, nullable, blank | 班级码（自动生成） |
| `created_by` | ForeignKey | to=User, on_delete=CASCADE, related_name='created_classes' | 创建者 |
| `created_at` | DateTimeField | auto_now_add=True | 创建时间 |
| `grade` | CharField | max_length=20, nullable, blank | 年级 |
| `description` | TextField | nullable, blank | 班级描述 |
| `homeroom_teacher` | ForeignKey | to=User, on_delete=SET_NULL, nullable, blank, related_name='homeroom_classes', limit_choices_to={'user_attribute': 2} | 班主任 |

**Meta选项**:
```python
db_table = 'userManageModule_classname'
verbose_name = '班级'
verbose_name_plural = '班级'
```

**模型方法**:

```python
def __str__(self):
    return self.name

def save(self, *args, **kwargs):
    """重写保存方法，自动生成班级码"""
    if not self.code:
        self.code = self.generate_unique_code()
    super().save(*args, **kwargs)

def generate_unique_code(self):
    """生成唯一班级码，格式：2字母+2数字+2字母"""
    # 例如：AB12CD
```

---

### 1.3 ClassTeacher (班级任课教师关联模型)

**功能描述**: 班级与任课教师的关联表，记录教师在不同班级教授的科目。

**表名**: `userManageModule_classteacher`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `class_obj` | ForeignKey | to=className, on_delete=CASCADE, related_name='teachers' | 班级 |
| `teacher` | ForeignKey | to=User, on_delete=CASCADE, limit_choices_to={'user_attribute': 2} | 教师 |
| `subject` | CharField | max_length=50 | 教授科目 |
| `created_at` | DateTimeField | auto_now_add=True | 创建时间 |

**Meta选项**:
```python
unique_together = ('class_obj', 'teacher', 'subject')  # 联合唯一约束
verbose_name = '任课教师'
```

---

## 2. 题目管理模块 (questionManageModule)

### 2.1 Problem (题目模型)

**功能描述**: 题目基本信息表，是题库管理的核心模型。

**表名**: `questionManageModule_problem`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `title` | CharField | max_length=200, nullable, blank | 题目标题 |
| `content` | ForeignKey | to=ProblemContent, on_delete=SET_NULL, nullable, blank, related_name='problems' | 题目内容 |
| `problem_type` | ForeignKey | to=ProblemType, on_delete=PROTECT | 题目类型 |
| `tags` | ManyToManyField | to=ProblemTag, blank | 题目标签 |
| `creator` | ForeignKey | to=User, on_delete=PROTECT, nullable, blank | 创建人 |
| `create_time` | DateTimeField | auto_now_add=True, nullable, blank | 创建时间 |
| `difficulty` | PositiveSmallIntegerField | choices=[(1,'简单'),(2,'中等'),(3,'困难')], default=2 | 难度 |
| `is_active` | BooleanField | default=True | 是否激活 |
| `subject` | ForeignKey | to=Subject, on_delete=PROTECT | 所属科目 |
| `points` | PositiveIntegerField | default=0, nullable, blank | 总分值 |
| `got_points` | PositiveIntegerField | default=0, nullable, blank | 获取的分数 |
| `scoringPoint` | ForeignKey | to=ScoringPoint, on_delete=SET_NULL, nullable, blank | 评分要则表 |
| `answer` | ForeignKey | to=Answer, on_delete=SET_NULL, nullable, blank | 答案 |
| `attachment` | ForeignKey | to=ProblemAttachment, on_delete=SET_NULL, nullable, blank | 附件 |
| `estimated_time` | PositiveIntegerField | default=5, nullable, blank | 预估耗时(分钟) |
| `knowledge_points` | ManyToManyField | to=KnowledgePoint, blank, related_name='problems' | 涉及知识点 |

**Meta选项**:
```python
ordering = ['-create_time']  # 按创建时间降序
indexes = [
    models.Index(fields=['problem_type']),
    models.Index(fields=['subject']),
    models.Index(fields=['difficulty']),
]
```

**难度等级说明**:

| difficulty | 描述 |
|------------|------|
| 1 | 简单 |
| 2 | 中等 |
| 3 | 困难 |

---

### 2.2 ProblemType (题目类型模型)

**功能描述**: 题目类型分类表（如选择题、填空题等）。

**表名**: `questionManageModule_problemtype`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `name` | CharField | max_length=50, unique | 类型名称 |
| `code` | CharField | max_length=20, unique | 类型代码 |
| `description` | TextField | blank | 类型描述 |
| `is_active` | BooleanField | default=True | 是否激活 |

**常见类型示例**:

| code | name | description |
|------|------|-------------|
| choice | 选择题 | 单选或多选题 |
| fill | 填空题 | 需填写答案 |
| short_answer | 简答题 | 简短文字回答 |
| calculation | 计算题 | 需要计算过程 |

---

### 2.3 ProblemContent (题目内容模型)

**功能描述**: 题目内容表，支持多种题型，使用JSON存储结构化数据。

**表名**: `questionManageModule_problemcontent`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `content` | TextField | verbose_name="题目内容text" | 题目内容文本 |
| `content_data` | JSONField | default=dict, blank | 题目内容JSON（存储选项、填空位置等） |
| `created_at` | DateTimeField | auto_now_add=True | 创建时间 |

**content_data JSON结构示例**:

```json
{
    "type": "choice",
    "options": {
        "A": "选项A内容",
        "B": "选项B内容",
        "C": "选项C内容",
        "D": "选项D内容"
    },
    "images": ["image_url_1", "image_url_2"]
}
```

---

### 2.4 Answer (答案模型)

**功能描述**: 题目答案表，存储标准答案和解析。

**表名**: `questionManageModule_answer`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `content` | TextField | verbose_name="答案内容text" | 答案内容（简洁版） |
| `content_data` | JSONField | default=dict, blank | 答案数据JSON |
| `explanation` | TextField | blank | 答案解析（详细版） |
| `updated_at` | DateTimeField | auto_now=True | 最新更新时间 |

**Meta选项**:
```python
verbose_name = "题目答案"
```

---

### 2.5 ScoringPoint (得分点模型)

**功能描述**: 题目得分点表，用于AI评分参考。

**表名**: `questionManageModule_scoringpoint`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `problem` | ForeignKey | to=Problem, on_delete=CASCADE | 关联题目 |
| `point` | CharField | max_length=200 | 得分点描述 |
| `point_key` | CharField | max_length=50, blank | 得分点标识 |
| `score` | FloatField | - | 分值 |
| `matching_rule` | JSONField | default=dict, blank | 匹配规则 |
| `order` | PositiveSmallIntegerField | default=0 | 排序 |

**Meta选项**:
```python
verbose_name = "得分点"
ordering = ['problem', 'order']
```

**matching_rule JSON结构示例**:

```json
{
    "keywords": ["关键词1", "关键词2"],
    "regex": "正则表达式",
    "similarity_threshold": 0.8
}
```

---

### 2.6 ProblemTag (题目标签模型)

**功能描述**: 题目标签分类表。

**表名**: `questionManageModule_problemtag`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `name` | CharField | max_length=50, unique | 标签名称 |
| `description` | TextField | blank | 描述 |
| `color` | CharField | max_length=20, default="#666666" | 标签颜色 |
| `created_at` | DateTimeField | auto_now_add=True | 创建时间 |

---

### 2.7 Subject (科目模型)

**功能描述**: 科目分类表（如数学、物理等）。

**表名**: `questionManageModule_subject`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `name` | CharField | max_length=100, unique | 科目名称 |
| `code` | CharField | max_length=50, unique | 科目代码 |
| `description` | TextField | blank, nullable | 描述 |

**常见科目示例**:

| code | name |
|------|------|
| math | 数学 |
| physics | 物理 |
| chemistry | 化学 |
| chinese | 语文 |
| english | 英语 |

---

### 2.8 ProblemAttachment (题目附件模型)

**功能描述**: 题目附件表，存储图片、文件等。

**表名**: `questionManageModule_problemattachment`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `file` | FileField | upload_to='problem_attachments/%Y/%m/%d/' | 附件文件 |
| `name` | CharField | max_length=100 | 附件名称 |
| `description` | TextField | blank | 描述 |
| `uploaded_at` | DateTimeField | auto_now_add=True | 上传时间 |

---

### 2.9 KnowledgePoint (知识点模型)

**功能描述**: 教学大纲层面的知识点模型，支持树状结构。

**表名**: `questionManageModule_knowledgepoint`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `subject` | ForeignKey | to=Subject, on_delete=CASCADE | 所属科目 |
| `name` | CharField | max_length=200 | 知识点名称 |
| `description` | TextField | blank | 知识点描述 |
| `parent` | ForeignKey | to='self', on_delete=SET_NULL, nullable, blank, related_name='children' | 父级知识点（树状结构） |

**Meta选项**:
```python
verbose_name = "知识点"
```

**树状结构示例**:

```
数学 (Subject)
├── 代数
│   ├── 方程
│   │   ├── 一元一次方程
│   │   └── 二元一次方程组
│   └── 函数
│       ├── 一次函数
│       └── 二次函数
└── 几何
    ├── 平面几何
    └── 立体几何
```

---

### 2.10 StudentMastery (学生掌握度模型)

**功能描述**: 学生知识点掌握度记录，核心分析表。

**表名**: `questionManageModule_studentmastery`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `student` | ForeignKey | to=User, on_delete=CASCADE, related_name='mastery_stats' | 学生 |
| `knowledge_point` | ForeignKey | to=KnowledgePoint, on_delete=CASCADE, related_name='student_stats' | 知识点 |
| `mastery_level` | FloatField | default=0.0 | 掌握度评分(1-5) |
| `total_questions_attempted` | PositiveIntegerField | default=0 | 练习题数 |
| `last_updated` | DateTimeField | auto_now=True | 更新时间 |

**Meta选项**:
```python
unique_together = ('student', 'knowledge_point')  # 联合唯一约束
verbose_name = "学生掌握度"
```

**掌握度等级说明**:

| mastery_level | 描述 |
|---------------|------|
| 1.0 - 2.0 | 未掌握 |
| 2.0 - 3.0 | 初步掌握 |
| 3.0 - 4.0 | 基本掌握 |
| 4.0 - 5.0 | 熟练掌握 |

---

## 3. 批改模块 (gradingModule)

### 3.1 Submission (提交记录模型)

**功能描述**: 学生做题提交记录模型，存储答题内容和批改结果。

**表名**: `gradingModule_submission`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `problem` | ForeignKey | to=Problem, on_delete=CASCADE, related_name='submissions' | 题目 |
| `student` | ForeignKey | to=User, on_delete=CASCADE, related_name='submissions' | 学生 |
| `submitted_text` | TextField | nullable, blank, default='' | 提交的文本 |
| `submitted_time` | DateTimeField | auto_now_add=True | 提交时间 |
| `submitted_image` | ImageField | upload_to='submissions/', nullable, blank, default="default_submissionImage.png" | 提交的图片 |
| `choose_answer` | TextField | nullable, blank | 选择题答案 |
| `status` | CharField | max_length=20, choices=STATUS_CHOICES, default='PENDING' | 状态 |
| `score` | FloatField | nullable, blank | 得分 |
| `feedback` | TextField | blank, nullable | 批改反馈 |
| `justification` | TextField | blank, nullable | AI评分理由 |

**状态选项 (STATUS_CHOICES)**:

| 状态值 | 描述 |
|--------|------|
| `PENDING` | 待批改 |
| `GRADING` | 批改中 |
| `SUBMITTED` | 已提交 |
| `GRADED` | 已批改 |
| `ACCEPTED` | 答案正确 |
| `WRONG_ANSWER` | 答案错误 |
| `COMPILE_ERROR` | 编译错误 |
| `RUNTIME_ERROR` | 运行错误 |

---

## 4. 作业管理模块 (assignmentAndClassModule)

### 4.1 Assignment (作业模型)

**功能描述**: 作业发布模型，用于班级作业管理。

**表名**: `assignmentAndClassModule_assignment`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `problem` | ForeignKey | to=Problem, on_delete=PROTECT, nullable, blank | 关联的题目 |
| `title` | CharField | max_length=200 | 作业标题 |
| `description` | TextField | nullable, blank | 作业描述 |
| `teacher` | ForeignKey | to=User, on_delete=CASCADE | 发布教师 |
| `target_class` | ForeignKey | to=className, on_delete=CASCADE | 目标班级 |
| `created_at` | DateTimeField | auto_now_add=True | 创建时间 |
| `deadline` | DateTimeField | nullable, blank, default=None | 截止时间 |
| `attachment` | FileField | upload_to='assignments/', nullable, blank | 附件 |

---

### 4.2 AssignmentStatus (作业状态模型)

**功能描述**: 学生作业完成状态模型。

**表名**: `assignmentAndClassModule_assignmentstatus`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `assignment` | ForeignKey | to=Assignment, on_delete=CASCADE | 作业 |
| `submission` | ForeignKey | to=Submission, on_delete=CASCADE, nullable, blank | 提交记录 |
| `student` | ForeignKey | to=User, on_delete=CASCADE | 学生 |
| `status` | CharField | max_length=20, choices=STATUS_CHOICES, default='pending' | 状态 |
| `submitted_at` | DateTimeField | nullable, blank | 提交时间 |

**状态选项 (STATUS_CHOICES)**:

| 状态值 | 描述 |
|--------|------|
| `pending` | 待完成 |
| `submitted` | 已提交 |
| `graded` | 已批改 |

---

## 5. BKT知识追踪模块 (BKTModule)

### 5.1 BKTKnowledgeModel (BKT知识点模型参数表)

**功能描述**: 存储每个知识点的BKT四个核心参数，用于知识追踪算法。

**表名**: `bkt_knowledge_model`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `knowledge_point` | OneToOneField | to=KnowledgePoint, on_delete=CASCADE, related_name='bkt_model' | 关联知识点 |
| `p_L0` | FloatField | default=0.1 | 初始掌握概率 (P(L₀)) |
| `p_T` | FloatField | default=0.3 | 学习转移概率 (P(T)) |
| `p_G` | FloatField | default=0.1 | 猜测概率 (P(G)) |
| `p_S` | FloatField | default=0.1 | 失误概率 (P(S)) |
| `training_samples` | PositiveIntegerField | default=0 | 训练样本数 |
| `last_trained` | DateTimeField | nullable, blank | 最后训练时间 |
| `decay_factor` | FloatField | default=0.95 | 遗忘衰减因子 |
| `created_at` | DateTimeField | auto_now_add=True | 创建时间 |
| `updated_at` | DateTimeField | auto_now=True | 更新时间 |

**BKT参数说明**:

| 参数 | 名称 | 范围 | 描述 |
|------|------|------|------|
| `p_L0` | 初始掌握概率 | 0-1 | 学生在未学习前对知识点已掌握的概率 |
| `p_T` | 学习转移概率 | 0-1 | 学生从未掌握到掌握的转移概率 |
| `p_G` | 猜测概率 | 0-1 | 学生未掌握但猜对的概率 |
| `p_S` | 失误概率 | 0-1 | 学生已掌握但答错的概率 |

**Meta选项**:
```python
db_table = 'bkt_knowledge_model'
indexes = [
    models.Index(fields=['knowledge_point']),
    models.Index(fields=['updated_at']),
]
```

**模型方法**:

```python
def to_dict(self):
    """转换为字典格式"""
    return {
        'p_L0': self.p_L0,
        'p_T': self.p_T,
        'p_G': self.p_G,
        'p_S': self.p_S,
    }
```

---

### 5.2 LearningTrace (学习轨迹记录表)

**功能描述**: 记录学生每次答题的详细过程，用于BKT计算。

**表名**: `bkt_learning_trace`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `student` | ForeignKey | to=User, on_delete=CASCADE, related_name='learning_traces' | 学生 |
| `knowledge_point` | ForeignKey | to=KnowledgePoint, on_delete=CASCADE, related_name='learning_traces' | 知识点 |
| `outcome` | CharField | max_length=10, choices=[('CORRECT','正确'),('INCORRECT','错误')] | 答题结果 |
| `submission_id` | PositiveIntegerField | nullable, blank | 关联提交ID |
| `attempt_time` | DateTimeField | auto_now_add=True | 答题时间 |
| `predicted_mastery_before` | FloatField | nullable, blank | 答题前预测掌握度 |
| `predicted_mastery_after` | FloatField | nullable, blank | 答题后预测掌握度 |

**Meta选项**:
```python
db_table = 'bkt_learning_trace'
ordering = ['-attempt_time']
indexes = [
    models.Index(fields=['student', 'knowledge_point']),
    models.Index(fields=['attempt_time']),
    models.Index(fields=['knowledge_point', 'outcome']),
]
```

---

### 5.3 BKTStudentState (学生知识点掌握状态表)

**功能描述**: 存储每个学生对每个知识点的实时掌握概率。

**表名**: `bkt_student_state`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `student` | ForeignKey | to=User, on_delete=CASCADE, related_name='bkt_states' | 学生 |
| `knowledge_point` | ForeignKey | to=KnowledgePoint, on_delete=CASCADE, related_name='bkt_states' | 知识点 |
| `mastery_probability` | FloatField | default=0.0 | 掌握概率(0-1) |
| `last_updated` | DateTimeField | auto_now=True | 最后更新时间 |
| `total_attempts` | PositiveIntegerField | default=0 | 总答题次数 |
| `correct_attempts` | PositiveIntegerField | default=0 | 正确次数 |
| `streak_length` | PositiveIntegerField | default=0 | 连续正确次数 |
| `predicted_performance` | FloatField | nullable, blank | 预测下次答题正确的概率 |

**Meta选项**:
```python
unique_together = ('student', 'knowledge_point')
db_table = 'bkt_student_state'
indexes = [
    models.Index(fields=['student', 'knowledge_point']),
    models.Index(fields=['mastery_probability']),
    models.Index(fields=['last_updated']),
]
```

**模型方法**:

```python
def update_from_outcome(self, outcome, bkt_params):
    """
    根据答题结果更新掌握概率（BKT核心算法）

    参数:
        outcome: 'CORRECT' 或 'INCORRECT'
        bkt_params: BKT参数字典 {'p_L0', 'p_T', 'p_G', 'p_S'}

    返回:
        更新后的掌握概率
    """
```

---

### 5.4 BKTClassAnalytics (班级知识点掌握分析表)

**功能描述**: 存储班级层面的知识点掌握统计信息。

**表名**: `bkt_class_analytics`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `class_identifier` | CharField | max_length=50 | 班级标识符 |
| `class_type` | CharField | max_length=10, choices=[('GRADE','年级'),('CLASS','班级')], default='CLASS' | 班级类型 |
| `knowledge_point` | ForeignKey | to=KnowledgePoint, on_delete=CASCADE | 知识点 |
| `student_count` | PositiveIntegerField | default=0 | 学生人数 |
| `average_mastery` | FloatField | default=0.0 | 平均掌握度 |
| `mastery_std` | FloatField | default=0.0 | 掌握度标准差 |
| `proficiency_rate` | FloatField | default=0.0 | 熟练率(掌握概率>0.8的学生比例) |
| `calculated_at` | DateTimeField | auto_now=True | 计算时间 |

**Meta选项**:
```python
unique_together = ('class_identifier', 'knowledge_point')
db_table = 'bkt_class_analytics'
```

---

### 5.5 MigrationHistory (BKT模块迁移历史记录)

**功能描述**: 用于跟踪数据迁移和模型更新状态。

**表名**: `bkt_migration_history`

**字段详情**:

| 字段名 | 类型 | 属性 | 描述 |
|--------|------|------|------|
| `id` | BigAutoField | primary_key | 主键 |
| `migration_type` | CharField | max_length=20, choices=MIGRATION_TYPES | 迁移类型 |
| `description` | TextField | - | 描述 |
| `status` | CharField | max_length=10, choices=[('PENDING','待处理'),('RUNNING','进行中'),('SUCCESS','成功'),('FAILED','失败')], default='PENDING' | 状态 |
| `started_at` | DateTimeField | auto_now_add=True | 开始时间 |
| `completed_at` | DateTimeField | nullable, blank | 完成时间 |
| `error_message` | TextField | blank, nullable | 错误信息 |
| `records_processed` | PositiveIntegerField | default=0 | 处理记录数 |

**Meta选项**:
```python
db_table = 'bkt_migration_history'
ordering = ['-started_at']
```

---

## 6. DKT深度知识追踪模块 (dkt_app)

> **注意**: 此模块不是 Django ORM 模型，而是 PyTorch 神经网络模型。

### 6.1 DKTModel (深度知识追踪模型)

**功能描述**: 基于GRU的深度知识追踪神经网络模型。

**文件路径**: `dkt_app/models.py`

**模型结构**:

```python
class DKTModel(nn.Module):
    def __init__(self, topic_size):
        super(DKTModel, self).__init__()
        self.topic_size = topic_size

        # GRU层
        self.rnn = nn.GRU(
            input_size=topic_size * 2,   # 输入维度：知识点数*2
            hidden_size=topic_size,       # 隐藏层维度：知识点数
            num_layers=1,
            batch_first=True
        )

        # 输出层
        self.score = nn.Linear(topic_size, 1)

    def forward(self, v, s, h):
        """
        前向传播

        参数:
            v: 题目向量 (batch_size, seq_len, topic_size)
            s: 得分向量 (batch_size, seq_len, topic_size)
            h: 隐藏状态 (1, batch_size, topic_size)

        返回:
            output: 预测得分
            hidden: 新的隐藏状态
        """
        pass

    def default_hidden(self):
        """初始化隐藏状态"""
        pass
```

---

### 6.2 DKT (DKT模型包装类)

**功能描述**: DKT模型的包装类。

**模型结构**:

```python
class DKT(nn.Module):
    def __init__(self, knowledge_n):
        super(DKT, self).__init__()
        self.knowledge_n = knowledge_n  # 知识点数量
        self.seq_model = DKTModel(knowledge_n)

    def forward(self, topic, score, hidden):
        """
        前向传播

        参数:
            topic: 题目序列
            score: 得分序列
            hidden: 隐藏状态

        返回:
            预测结果
        """
        pass
```

---

## 7. 模型关系图谱

### 7.1 ER关系图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              用户管理模块                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐           │
│  │     User     │◄───────►│   className  │◄────────│ ClassTeacher │           │
│  └──────────────┘ M:N     └──────────────┘         └──────────────┘           │
│         │                       │                          │                    │
│         │ created_by            │ homeroom_teacher         │ teacher           │
│         │                       │                          │                    │
│         │                  ┌────┴────┐               ┌─────┘                   │
│         │                  │         │               │                         │
│         └──────────────────┤         ├───────────────┘                         │
│                            │         │                                         │
│                     created_classes │ class_obj                                │
│                            │         │                                         │
└────────────────────────────┴─────────┴─────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              题目管理模块                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐                                                               │
│  │    Problem   │◄──────────────────────────────────────────────────────────┐  │
│  └──────────────┘                                                           │  │
│    │ │ │ │ │ │ │                                                           │  │
│    │ │ │ │ │ │ └───────────► ┌────────────────┐                            │  │
│    │ │ │ │ │      knowledge  │ KnowledgePoint │◄───┐                       │  │
│    │ │ │ │ │      _points    └────────────────┘    │                       │  │
│    │ │ │ │ │                      │                │                       │  │
│    │ │ │ │ │                      │ subject        │ parent                │  │
│    │ │ │ │ │                      ▼                │                       │  │
│    │ │ │ │ │               ┌────────────┐         │                       │  │
│    │ │ │ │ │               │  Subject   │         │                       │  │
│    │ │ │ │ │               └────────────┘         │                       │  │
│    │ │ │ │ │                                      │                       │  │
│    │ │ │ │ └───────────► ┌──────────────┐        │                       │  │
│    │ │ │ │    answer       │    Answer    │        │                       │  │
│    │ │ │ └─────────────► ┌──────────────┐        │                       │  │
│    │ │ │    attachment    │ProblemAttach │        │                       │  │
│    │ │ └───────────────► ┌──────────────┐        │                       │  │
│    │ │     content       │ProblemContent│        │                       │  │
│    │ └─────────────────► ┌──────────────┐        │                       │  │
│    │      problem_type   │ ProblemType  │        │                       │  │
│    └───────────────────► ┌──────────────┐        │                       │  │
│          creator         │     User     │        │                       │  │
│                          └──────────────┘        │                       │  │
│                                                   │                       │  │
│  ┌────────────────┐                              │                       │  │
│  │ StudentMastery │──────────────────────────────┘                       │  │
│  └────────────────┘  knowledge_point                                      │  │
│         │                                                                 │  │
│         │ student                                                         │  │
│         ▼                                                                 │  │
│  ┌──────────────┐                                                         │  │
│  │     User     │                                                         │  │
│  └──────────────┘                                                         │  │
│                                                                           │  │
└───────────────────────────────────────────────────────────────────────────┘──┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              批改 & 作业模块                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐           │
│  │     User     │◄────────│ Submission   │────────►│   Problem    │           │
│  └──────────────┘ student └──────────────┘ problem └──────────────┘           │
│         ▲                              │                                        │
│         │                              │                                        │
│         │                      ┌───────┴───────┐                               │
│         │                      │               │                               │
│  ┌──────┴──────┐        ┌──────┴─────┐  ┌──────┴─────┐                        │
│  │Assignment   │        │ Assignment │  │Assignment  │                        │
│  │Status       │        │            │  │Status      │                        │
│  └─────────────┘        └────────────┘  └────────────┘                        │
│         │                      │                                                │
│         │ assignment           │ student                                        │
│         │                      │                                                │
│         │               ┌──────┴───────┐                                       │
│         └──────────────►│     User     │                                       │
│                         └──────────────┘                                       │
│                                                                                │
│  ┌──────────────┐                                                              │
│  │  Assignment  │───────────► ┌──────────────┐                                │
│  └──────────────┘ target_class │   className  │                                │
│         │                     └──────────────┘                                │
│         │ problem                                                              │
│         ▼                                                                      │
│  ┌──────────────┐                                                              │
│  │   Problem    │                                                              │
│  └──────────────┘                                                              │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BKT知识追踪模块                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────┐          ┌──────────────────┐                            │
│  │ BKTKnowledgeModel│ 1:1      │  KnowledgePoint  │                            │
│  └──────────────────┴─────────►└──────────────────┘                            │
│                                        ▲                                        │
│                                        │                                        │
│         ┌──────────────────────────────┼──────────────────────────────┐        │
│         │                              │                              │        │
│  ┌──────┴───────┐              ┌───────┴──────┐              ┌───────┴──────┐ │
│  │ LearningTrace│              │BKTStudentState│              │BKTClassAnalytics│
│  └──────────────┘              └──────────────┘              └──────────────┘ │
│         │                              │                              │        │
│         │ student                      │ student                      │        │
│         ▼                              ▼                              │        │
│  ┌──────────────┐              ┌──────────────┐                     │        │
│  │     User     │              │     User     │                     │        │
│  └──────────────┘              └──────────────┘                     │        │
│                                                                       │        │
│                                         class_identifier             │        │
│                                         ┌─────────────────────────────┘        │
│                                         │                                      │
│                                   ┌─────┴─────┐                               │
│                                   │ className │                               │
│                                   └───────────┘                               │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 核心关系汇总表

| 关系类型 | 源模型 | 目标模型 | 字段名 | 说明 |
|---------|--------|---------|--------|------|
| ForeignKey | User | className | created_classes | 用户创建的班级 |
| ForeignKey | className | User | homeroom_teacher | 班级的班主任 |
| ManyToMany | User | className | class_in | 学生所属班级 |
| ForeignKey | Problem | User | creator | 题目创建人 |
| ForeignKey | Problem | Subject | subject | 题目所属科目 |
| ManyToMany | Problem | KnowledgePoint | knowledge_points | 题目涉及的知识点 |
| ForeignKey | Problem | ProblemType | problem_type | 题目类型 |
| ForeignKey | Problem | Answer | answer | 题目答案 |
| ForeignKey | Submission | Problem | problem | 提交关联的题目 |
| ForeignKey | Submission | User | student | 提交的学生 |
| ForeignKey | Assignment | Problem | problem | 作业关联的题目 |
| ForeignKey | Assignment | className | target_class | 作业目标班级 |
| ForeignKey | Assignment | User | teacher | 发布教师 |
| OneToOne | BKTKnowledgeModel | KnowledgePoint | knowledge_point | BKT参数关联知识点 |
| ForeignKey | BKTStudentState | User | student | 学生BKT状态 |
| ForeignKey | BKTStudentState | KnowledgePoint | knowledge_point | 知识点BKT状态 |
| ForeignKey | LearningTrace | User | student | 学习轨迹学生 |
| ForeignKey | LearningTrace | KnowledgePoint | knowledge_point | 学习轨迹知识点 |
| ForeignKey | StudentMastery | User | student | 学生掌握度 |
| ForeignKey | StudentMastery | KnowledgePoint | knowledge_point | 知识点掌握度 |
| ForeignKey | KnowledgePoint | Subject | subject | 知识点所属科目 |
| ForeignKey | KnowledgePoint | KnowledgePoint | parent | 知识点父级（树状） |

---

## 8. 索引与约束

### 8.1 唯一约束

| 模型 | 字段组合 | 约束类型 |
|------|----------|----------|
| User | uid | UNIQUE |
| User | openid | UNIQUE |
| className | code | UNIQUE |
| ClassTeacher | (class_obj, teacher, subject) | UNIQUE_TOGETHER |
| StudentMastery | (student, knowledge_point) | UNIQUE_TOGETHER |
| BKTStudentState | (student, knowledge_point) | UNIQUE_TOGETHER |
| BKTClassAnalytics | (class_identifier, knowledge_point) | UNIQUE_TOGETHER |
| ProblemType | name, code | UNIQUE |
| Subject | name, code | UNIQUE |
| ProblemTag | name | UNIQUE |
| KnowledgePoint | - | - (无唯一约束) |

### 8.2 数据库索引

| 模型 | 索引字段 | 说明 |
|------|----------|------|
| Problem | problem_type, subject, difficulty | 查询优化 |
| BKTKnowledgeModel | knowledge_point, updated_at | BKT查询优化 |
| LearningTrace | (student, knowledge_point), attempt_time, (knowledge_point, outcome) | 学习轨迹查询 |
| BKTStudentState | (student, knowledge_point), mastery_probability, last_updated | 状态查询优化 |

### 8.3 外键约束行为

| 行为 | 说明 | 使用场景 |
|------|------|----------|
| CASCADE | 级联删除 | 删除用户时删除其提交记录 |
| PROTECT | 禁止删除 | 有题目的题型不能删除 |
| SET_NULL | 设为NULL | 班主任删除后班级的班主任字段设为NULL |
| DO_NOTHING | 无操作 | 通常不推荐使用 |

---

## 附录：统计信息

- **Django ORM 模型总数**: 18个
- **PyTorch 神经网络模型**: 2个
- **ForeignKey 关系**: 25个
- **ManyToMany 关系**: 4个
- **OneToOne 关系**: 1个
- **自引用关系**: 1个 (KnowledgePoint.parent)
- **联合唯一约束**: 4个
