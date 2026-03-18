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
    STATUS_CHOICES = [
        ('pending', '待完成'),
        ('submitted', '已提交'),
        ('graded', '已批改'),
    ]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE,null=True, blank=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="提交时间")
