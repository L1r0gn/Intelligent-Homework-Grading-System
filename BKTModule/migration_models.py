from django.db import models


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