from django.db import models
from questionManageModule.models import Problem
from userManageModule.models import User


class Submission(models.Model):
    """做题记录（提交记录）模型。

    ★ 批改状态的唯一权威定义在这里，任何其他模块都必须引用本类常量，
      不允许再出现裸字符串（如 'ACCEPTED'、'processing'）。

    状态字段只描述「批改流程走到哪一步」，不描述「答案对不对」：

        PENDING         待批改：已提交，等待 Celery 批改任务取走
        GRADING         批改中：批改任务已开始处理
        GRADED          已批改：批改完成，score 已写入（终态）
        COMPILE_ERROR   编译错误：批改无法进行（终态）
        RUNTIME_ERROR   运行错误：批改过程异常（终态）

    为什么不把「答案正确 / 答案错误」也做成状态：
        主观题由视觉大模型打分，结果是连续分数（例如 7/10），
        "对/错"只能由得分率派生；一旦把 ACCEPTED / WRONG_ANSWER 塞进状态位，
        就会出现「GRADED 与 ACCEPTED 并存、谁该被写入」的分裂（历史遗留问题）。
        因此对错统一由 `is_correct` 从 score 派生，不占用状态位。
    """

    # ---- 状态取值 ----------------------------------------------------------
    STATUS_PENDING = 'PENDING'
    STATUS_GRADING = 'GRADING'
    STATUS_GRADED = 'GRADED'
    STATUS_COMPILE_ERROR = 'COMPILE_ERROR'
    STATUS_RUNTIME_ERROR = 'RUNTIME_ERROR'

    STATUS_CHOICES = [
        (STATUS_PENDING, '待批改'),
        (STATUS_GRADING, '批改中'),
        (STATUS_GRADED, '已批改'),
        (STATUS_COMPILE_ERROR, '编译错误'),
        (STATUS_RUNTIME_ERROR, '运行错误'),
    ]

    # ---- 状态分组（供查询、统计、模板判断复用） ---------------------------
    # 已进入批改队列但还没出结果
    STATUS_IN_PROGRESS = frozenset({STATUS_PENDING, STATUS_GRADING})
    # 批改失败：不会再自动推进，需要人工重新批改
    STATUS_FAILED = frozenset({STATUS_COMPILE_ERROR, STATUS_RUNTIME_ERROR})
    # 终态：不会再自动变化
    STATUS_TERMINAL = frozenset({STATUS_GRADED}) | STATUS_FAILED

    # ---- 判定规则 ----------------------------------------------------------
    # 得分率达到该阈值即视为「答对」。客观题答对得满分（比率 1.0），
    # 主观题允许部分给分，与 BKT / 掌握度分析共用同一阈值，避免口径不一。
    CORRECT_RATIO_THRESHOLD = 0.6

    # 历史遗留状态 → 现行状态。
    # 仅用于数据迁移和历史数据的容错读取，新代码不得再写入左侧取值。
    LEGACY_STATUS_ALIASES = {
        'SUBMITTED': STATUS_PENDING,
        'ACCEPTED': STATUS_GRADED,
        'WRONG_ANSWER': STATUS_GRADED,
    }

    # 关联字段
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions', verbose_name="题目")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions', verbose_name="学生")
    # 提交内容
    submitted_text = models.TextField(verbose_name="提交的文本", null=True, blank=True, default='')
    submitted_time = models.DateTimeField(auto_now_add=True, verbose_name="提交时间")
    submitted_image = models.ImageField(
        upload_to='submissions/',
        blank=True,
        null=True,
        # 不要给字符串默认值（如 "default_submissionImage.png"）：
        # FileField 的默认值会被当成真实文件路径，未上传图片时字段依然 truthy，
        # 导致 tasks.py 里 "if not submission.submitted_image" 的判空永不生效，
        # 主观题会把占位图当成学生答卷送去批改。
        default=None,
        verbose_name="提交图片",
    )
    choose_answer = models.TextField(verbose_name="提交的选择题答案", null=True, blank=True)
    # 批改结果
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="批改状态",
        help_text="仅表示批改流程进度；答案对错请使用 is_correct",
    )
    score = models.FloatField(null=True, blank=True, verbose_name="得分")
    feedback = models.TextField(blank=True, null=True, verbose_name="批改反馈")  # 可存储编译错误信息、测试用例结果等
    # 用于存储AI的评分理由
    justification = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.student.username} - {self.problem.title} ({self.status})'

    # ---- 状态辅助方法 ------------------------------------------------------
    @classmethod
    def normalize_status(cls, raw):
        """把任意来源（旧数据、前端传参）的状态值归一为现行取值。

        未知值原样返回（大写化），由调用方决定是忽略还是报错——
        沉默地改写成某个默认值会让脏数据藏起来。
        """
        if raw is None:
            return cls.STATUS_PENDING
        code = str(raw).strip().upper()
        if not code:
            return cls.STATUS_PENDING
        return cls.LEGACY_STATUS_ALIASES.get(code, code)

    @classmethod
    def status_filter_values(cls, raw):
        """把前端筛选值展开成数据库中可能存在的全部等价取值。

        迁移之后库里只有新取值；但对未迁移的环境仍要能筛出历史数据，
        所以这里额外带上旧别名，查询结果再统一归一。
        """
        code = cls.normalize_status(raw)
        values = {code}
        values.update(old for old, new in cls.LEGACY_STATUS_ALIASES.items() if new == code)
        return values

    @property
    def is_graded(self):
        """批改是否已产出结果（终态且拿到了分数）。"""
        return self.status == self.STATUS_GRADED

    @property
    def is_failed(self):
        """批改是否失败。"""
        return self.status in self.STATUS_FAILED

    @property
    def score_ratio(self):
        """得分率（0~1）；无法计算时返回 None。"""
        if self.score is None:
            return None
        full = getattr(self.problem, 'points', None) if self.problem_id else None
        if not full or full <= 0:
            return None
        return max(0.0, min(1.0, float(self.score) / float(full)))

    @property
    def is_correct(self):
        """答案是否正确——由批改结果派生，不作为独立状态存储。

        只有「已批改且有分数」的提交才能判定对错；
        待批改/批改中/批改失败一律返回 False（未知不等于错误，
        调用方若需区分"未判定"，请先判断 is_graded）。
        """
        if not self.is_graded:
            return False
        ratio = self.score_ratio
        return ratio is not None and ratio >= self.CORRECT_RATIO_THRESHOLD

    @property
    def status_text(self):
        """状态的中文展示名，等价于 get_status_display()。"""
        return self.get_status_display()
