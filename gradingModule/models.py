from django.db import models
from questionManageModule.models import Problem
from userManageModule.models import User
# Create your models here.
class Submission(models.Model):
    """做题记录（提交记录）模型"""
    # 定义提交状态的选项
    STATUS_CHOICES = [
        ('PENDING', '待批改'),
        ('GRADING', '批改中'),
        ('ACCEPTED', '通过'),
        ('WRONG_ANSWER', '答案错误'),
        ('COMPILE_ERROR', '编译错误'),
        ('RUNTIME_ERROR', '运行错误'),
    ]
    # 关联字段
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions', verbose_name="题目")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions', verbose_name="学生")
    # 提交内容
    submitted_text = models.TextField(verbose_name="提交的文本")
    submitted_time = models.DateTimeField(auto_now_add=True, verbose_name="提交时间")
    # 批改结果
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="状态")
    score = models.FloatField(null=True, blank=True, verbose_name="得分")
    feedback = models.TextField(blank=True, null=True, verbose_name="批改反馈") # 可以存储编译错误信息、测试用例结果等
    # class Meta:
    #     ordering = ['-submitted_at'] # 默认按提交时间降序排列
    #     verbose_name = "提交记录"
    #     verbose_name_plural = verbose_name
    def __str__(self):
        return f'{self.student.username} - {self.problem.title} ({self.status})'
