from django.db import models
from userManageModule.models import User
from questionManageModule.models import KnowledgePoint
import json


class BKTKnowledgeModel(models.Model):
    """
    BKT知识点模型参数表
    存储每个知识点的BKT四个核心参数 :
    p_L0 : 初始掌握概率(Prior)
    p_T : 学习转移概率(Learn)
    p_G : 猜测概率(Guess)
    p_S : 失误概率(Slip)
    """
    knowledge_point = models.OneToOneField(
        KnowledgePoint,
        on_delete=models.CASCADE,
        related_name='bkt_model',
        verbose_name="关联知识点"
    )
    
    # BKT核心参数 (0-1之间的概率值)
    p_L0 = models.FloatField(
        default=0.1,
        verbose_name="初始掌握概率(Prior)",
        help_text="学生初次接触该知识点时的掌握概率"
    )
    p_T = models.FloatField(
        default=0.3,
        verbose_name="学习转移概率(Learn)",
        help_text="未掌握状态下通过学习达到掌握的概率"
    )
    p_G = models.FloatField(
        default=0.1,
        verbose_name="猜测概率(Guess)",
        help_text="未掌握但答对题目的概率"
    )
    p_S = models.FloatField(
        default=0.1,
        verbose_name="失误概率(Slip)",
        help_text="已掌握但答错题目的概率"
    )
    
    # 模型统计信息
    training_samples = models.PositiveIntegerField(
        default=0,
        verbose_name="训练样本数"
    )
    last_trained = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="最后训练时间"
    )
    
    # 扩展参数
    decay_factor = models.FloatField(
        default=0.95,
        verbose_name="遗忘衰减因子",
        help_text="知识遗忘的速度因子(0-1)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "BKT知识点模型"
        verbose_name_plural = "BKT知识点模型"
        db_table = 'bkt_knowledge_model'
        indexes = [
            models.Index(fields=['knowledge_point']),
            models.Index(fields=['-updated_at']),
        ]
    
    def __str__(self):
        return f"BKT模型-{self.knowledge_point.name}"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'p_L0': self.p_L0,
            'p_T': self.p_T,
            'p_G': self.p_G,
            'p_S': self.p_S,
            'decay_factor': self.decay_factor
        }


class LearningTrace(models.Model):
    """
    学习轨迹记录表
    记录学生每次答题的详细过程，用于BKT计算
    """
    OUTCOME_CHOICES = [
        ('CORRECT', '正确'),
        ('INCORRECT', '错误'),
    ]
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='learning_traces',
        verbose_name="学生"
    )
    knowledge_point = models.ForeignKey(
        KnowledgePoint,
        on_delete=models.CASCADE,
        related_name='learning_traces',
        verbose_name="知识点"
    )
    
    # 答题结果
    outcome = models.CharField(
        max_length=10,
        choices=OUTCOME_CHOICES,
        verbose_name="答题结果"
    )
    
    # 关联的提交记录（可选）
    submission_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="关联提交ID"
    )
    
    # 时间戳
    attempt_time = models.DateTimeField(auto_now_add=True, verbose_name="答题时间")
    
    # BKT计算相关字段
    predicted_mastery_before = models.FloatField(
        null=True,
        blank=True,
        verbose_name="答题前预测掌握度"
    )
    predicted_mastery_after = models.FloatField(
        null=True,
        blank=True,
        verbose_name="答题后预测掌握度"
    )
    
    class Meta:
        verbose_name = "学习轨迹记录"
        verbose_name_plural = "学习轨迹记录"
        db_table = 'bkt_learning_trace'
        indexes = [
            models.Index(fields=['student', 'knowledge_point']),
            models.Index(fields=['-attempt_time']),
            models.Index(fields=['knowledge_point', 'outcome']),
        ]
        ordering = ['-attempt_time']
    
    def __str__(self):
        return f"{self.student.username}-{self.knowledge_point.name}-{'✓' if self.outcome == 'CORRECT' else '✗'}"


class BKTStudentState(models.Model):
    """
    学生知识点掌握状态表
    存储每个学生对每个知识点的实时掌握概率
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bkt_states',
        verbose_name="学生"
    )
    knowledge_point = models.ForeignKey(
        KnowledgePoint,
        on_delete=models.CASCADE,
        related_name='bkt_states',
        verbose_name="知识点"
    )
    
    # 核心状态概率
    mastery_probability = models.FloatField(
        default=0.0,
        verbose_name="掌握概率",
        help_text="学生掌握该知识点的概率(0-1)"
    )
    
    # 状态更新时间
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")
    
    # 统计信息
    total_attempts = models.PositiveIntegerField(default=0, verbose_name="总答题次数")
    correct_attempts = models.PositiveIntegerField(default=0, verbose_name="正确次数")
    streak_length = models.PositiveIntegerField(default=0, verbose_name="连续正确次数")
    
    # 预测信息
    predicted_performance = models.FloatField(
        null=True,
        blank=True,
        verbose_name="预测表现",
        help_text="预测下次答题正确的概率"
    )
    
    class Meta:
        unique_together = ('student', 'knowledge_point')
        verbose_name = "学生BKT状态"
        verbose_name_plural = "学生BKT状态"
        db_table = 'bkt_student_state'
        indexes = [
            models.Index(fields=['student', 'knowledge_point']),
            models.Index(fields=['-mastery_probability']),
            models.Index(fields=['-last_updated']),
        ]
    
    def __str__(self):
        return f"{self.student.username}-{self.knowledge_point.name}: {self.mastery_probability:.2f}"
    
    def update_from_outcome(self, outcome, bkt_params=None):
        """
        根据答题结果更新掌握概率（BKT核心算法）
        """
        from .bkt_engine import BKTEngine
        
        if bkt_params is None:
            # 获取默认BKT参数
            bkt_model, created = BKTKnowledgeModel.objects.get_or_create(
                knowledge_point=self.knowledge_point
            )
            bkt_params = bkt_model.to_dict()
        
        # 执行BKT更新
        engine = BKTEngine(bkt_params)
        new_prob = engine.update_mastery_probability(
            self.mastery_probability,
            outcome == 'CORRECT'
        )
        
        # 更新统计信息
        self.mastery_probability = new_prob
        self.total_attempts += 1
        if outcome == 'CORRECT':
            self.correct_attempts += 1
            self.streak_length += 1
        else:
            self.streak_length = 0
            
        # 计算预测表现
        self.predicted_performance = engine.predict_next_performance(new_prob)
        
        self.save()
        return new_prob


class BKTClassAnalytics(models.Model):
    """
    班级知识点掌握分析表
    存储班级层面的知识点掌握统计信息
    """
    CLASS_ID_CHOICES = [
        ('GRADE', '年级'),
        ('CLASS', '班级'),
    ]
    
    class_identifier = models.CharField(
        max_length=50,
        verbose_name="班级标识符"
    )
    class_type = models.CharField(
        max_length=10,
        choices=CLASS_ID_CHOICES,
        default='CLASS',
        verbose_name="班级类型"
    )
    knowledge_point = models.ForeignKey(
        KnowledgePoint,
        on_delete=models.CASCADE,
        verbose_name="知识点"
    )
    
    # 统计指标
    student_count = models.PositiveIntegerField(default=0, verbose_name="学生人数")
    average_mastery = models.FloatField(default=0.0, verbose_name="平均掌握度")
    mastery_std = models.FloatField(default=0.0, verbose_name="掌握度标准差")
    proficiency_rate = models.FloatField(
        default=0.0,
        verbose_name="熟练率",
        help_text="掌握概率>0.8的学生比例"
    )
    
    # 更新时间
    calculated_at = models.DateTimeField(auto_now=True, verbose_name="计算时间")
    
    class Meta:
        unique_together = ('class_identifier', 'knowledge_point')
        verbose_name = "班级BKT分析"
        verbose_name_plural = "班级BKT分析"
        db_table = 'bkt_class_analytics'
        indexes = [
            models.Index(fields=['class_identifier', 'class_type']),
            models.Index(fields=['knowledge_point']),
            models.Index(fields=['-calculated_at']),
        ]
    
    def __str__(self):
        return f"{self.class_identifier}-{self.knowledge_point.name}: {self.average_mastery:.2f}"


class MigrationHistory(models.Model):
    """
    BKT模块迁移历史记录
    用于跟踪数据迁移和模型更新状态
    """
    MIGRATION_TYPES = [
        ('INITIAL', '初始数据迁移'),
        ('PARAMETER_UPDATE', '参数更新'),
        ('DATA_CLEANUP', '数据清理'),
        ('MODEL_CHANGE', '模型变更'),
    ]
    
    migration_type = models.CharField(max_length=20, choices=MIGRATION_TYPES, verbose_name="迁移类型")
    description = models.TextField(verbose_name="描述")
    status = models.CharField(
        max_length=10,
        choices=[('PENDING', '待处理'), ('RUNNING', '进行中'), ('SUCCESS', '成功'), ('FAILED', '失败')],
        default='PENDING',
        verbose_name="状态"
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")
    records_processed = models.PositiveIntegerField(default=0, verbose_name="处理记录数")
    
    class Meta:
        verbose_name = "迁移历史"
        verbose_name_plural = "迁移历史"
        db_table = 'bkt_migration_history'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.migration_type} - {self.status}"