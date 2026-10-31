from django.db import models

from gradingModule.models import Submission
from userManageModule.models import User,className
from questionManageModule.models import Problem


class Assignment(models.Model): # for class
    # django has id
    problem = models.ForeignKey(
        Problem,
        on_delete=models.PROTECT,  # 保护题目，如果已布置为作业，则不允许删除题库中的原题
        verbose_name="关联的题目",
        null=True,  # 允许创建"传统"作业（仅附件）
        blank=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    target_class = models.ForeignKey(className, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True,default=None)
    attachment = models.FileField(upload_to='assignments/', null=True, blank=True)
    custom_prompt = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="自定义评分提示词",
        help_text="教师自定义的AI评分提示词，用于增强批改反馈"
    )

class AssignmentStatus(models.Model): # for student
    """学生在某次作业下的提交状态。

    注意：本模型自迁移 0007 起**没有 status 字段**——作业的批改进度完全由
    关联的 Submission.status 决定，不要在这里再维护第二份状态（会立刻不同步）。

    下面这个常量只用于「学生尚未提交」这一作业侧情形，
    它不属于 Submission.status 的取值域，避免把"没交"和"待批改"混成一个值。
    """
    NOT_SUBMITTED = 'NOT_SUBMITTED'

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE,null=True, blank=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="提交时间")

    class Meta:
        verbose_name = "学生作业状态"
        verbose_name_plural = verbose_name
        # 同一学生在同一作业下只能有一条状态记录。
        # 之前没有任何唯一约束，并发提交时 get_or_create 会插出重复行，
        # 而读取侧统一用 .filter(...).first()，学生看到的状态会随机跳变。
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'student'],
                name='uniq_assignmentstatus_assignment_student',
            ),
        ]
