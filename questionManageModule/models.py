from django.db import models
from userManageModule.models import User


class Problem(models.Model):
    #题目基本信息表
    DIF_CHOICES = [
        (1, '简单'),
        (2, '中等'),
        (3, '困难'),
    ]
    title = models.CharField(max_length=200, verbose_name="题目标题",blank=True,null=True)
    # 保留正向关联（一个 Problem 关联一个 ProblemContent）
    content = models.ForeignKey(
        'ProblemContent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='题目内容',
        related_name='problems'  # 反向引用名，避免冲突
    )
    problem_type = models.ForeignKey('ProblemType', on_delete=models.PROTECT, verbose_name="题目类型(选择……)")
    tags = models.ManyToManyField('ProblemTag', blank=True, verbose_name="题目标签")
    creator = models.ForeignKey('userManageModule.User', on_delete=models.PROTECT, verbose_name="创建人", null=True,blank = True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", null=True,blank = True)
    difficulty = models.PositiveSmallIntegerField(choices=DIF_CHOICES, default=2, verbose_name="难度")
    #is_active = models.BooleanField(default=True, verbose_name="是否激活") #是否可见
    subject = models.ForeignKey('Subject', on_delete=models.PROTECT, verbose_name="所属科目")
    points = models.PositiveIntegerField(default=0, verbose_name="总共的分值" , null=True , blank=True )
    got_points = models.PositiveIntegerField(default=0,verbose_name='获取的分数',null=True , blank=True )
    scoringPoint = models.ForeignKey('ScoringPoint',verbose_name='评分要则表',on_delete=models.SET_NULL,null = True,blank = True)
    answer = models.ForeignKey('Answer',verbose_name='答案，用于评析',on_delete=models.SET_NULL,null=True,blank = True)
    attachment = models.ForeignKey('ProblemAttachment',verbose_name='附件',on_delete=models.SET_NULL,null = True,blank = True)
    estimated_time = models.PositiveIntegerField(
        default=5, verbose_name="预估耗时(分钟)",
        help_text="预计学生完成此题需要的时间(分钟)",
        null=True,blank = True
    )
    class Meta:
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['problem_type']),
            models.Index(fields=['subject']),
            models.Index(fields=['difficulty']),
        ]
    def __str__(self):
        return f"{self.id}-{self.title}"

class ProblemType(models.Model):
    #题目类型表
    name = models.CharField(max_length=50, unique=True, verbose_name="类型名称")
    code = models.CharField(max_length=20, unique=True, verbose_name="类型代码")
    description = models.TextField(blank=True, verbose_name="类型描述")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    def __str__(self):
        return self.name

class ProblemContent(models.Model):
    """题目内容表，支持多种题型"""
    # problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="contents",null=True,blank=True)
    content = models.TextField(verbose_name="题目内容text")
    # 使用JSON字段存储题目特定的结构化数据(如选择题选项、填空题空白位置等)
    content_data = models.JSONField(default=dict, blank=True, verbose_name="题目内容json")
    created_at = models.DateTimeField(auto_now_add=True,verbose_name='创建时间')
    def __str__(self):
        return f"{self.id}"

class Answer(models.Model):
    """题目答案表"""
    # problem = models.OneToOneField(Problem, on_delete=models.CASCADE, related_name="answer")
    content = models.TextField(verbose_name="答案内容text(简洁：选择填空)")
    # 使用JSON字段存储结构化答案(如选择题的正确选项、填空题的填空答案等)
    content_data = models.JSONField(default=dict, blank=True, verbose_name="答案数据json")
    explanation = models.TextField(blank=True, verbose_name="答案解析text(应该是详细些的)")
    updated_at = models.DateTimeField(auto_now=True,verbose_name='最新更新时间')
    class Meta:
        verbose_name = "题目答案"
        verbose_name_plural = "题目答案"
    def __str__(self):
        return f"答案-{self.id}"
class ScoringPoint(models.Model):
    """题目得分点表"""             """暂时不太需要，现在用ai评分"""
    # problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="scoring_points")
    point = models.CharField(max_length=200, verbose_name="得分点描述")
    point_key = models.CharField(
        max_length=50, blank=True, verbose_name="得分点标识",
        help_text="用于程序自动批改时识别得分点"
    )
    score = models.FloatField(verbose_name="分值")
    # 使用JSON字段存储得分点的匹配规则(用于自动批改)
    matching_rule = models.JSONField(default=dict, blank=True, verbose_name="匹配规则")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="排序")
    class Meta:
        verbose_name = "得分点"
        verbose_name_plural = "得分点"
        ordering = ['problem', 'order']
    def __str__(self):
        return f"{self.id}-{self.point}"
class ProblemTag(models.Model):
    """题目标签表"""
    name = models.CharField(max_length=50, unique=True, verbose_name="标签名称")
    description = models.TextField(blank=True, verbose_name="描述")
    color = models.CharField(max_length=20, default="#666666", verbose_name="标签颜色")
    created_at = models.DateTimeField(auto_now_add=True,verbose_name="最新更新时间")
    class Meta:
        verbose_name = "题目标签"
        verbose_name_plural = "题目标签"
    def __str__(self):
        return self.name
class Subject(models.Model):
    """科目表"""
    name = models.CharField(max_length=100, unique=True, verbose_name="科目名称")
    code = models.CharField(max_length=50, unique=True, verbose_name="科目代码")
    description = models.TextField(blank=True, verbose_name="描述",null=True)
    def __str__(self):
        return self.name
class ProblemAttachment(models.Model):
    """题目附件表"""
    # problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to='problem_attachments/%Y/%m/%d/', verbose_name="附件")
    name = models.CharField(max_length=100, verbose_name="附件名称")
    description = models.TextField(blank=True, verbose_name="描述")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.id}-{self.name}"
