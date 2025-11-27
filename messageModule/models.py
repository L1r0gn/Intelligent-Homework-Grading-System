from django.db import models
from userManageModule.models import User

class Message(models.Model):
    """通知消息模型"""
    # 发送者
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )

    # 接收者（可以是单个学生或多个学生，这里用多对多）
    receivers = models.ManyToManyField(
        User,
        related_name="received_messages",
    )
    # 通知标题
    title = models.CharField(max_length=200, verbose_name="通知标题")
    # 通知内容
    content = models.TextField(max_length=200,verbose_name="通知内容")
    # 发布时间（自动记录创建时间）
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="发布时间")

    def __str__(self):
        return f"{self.sender.username}发布的<{self.title}>"

    class Meta:
        verbose_name = "通知消息"
        verbose_name_plural = "通知消息"
        ordering = ["-created_time"]  # 按发布时间倒序排列（最新的在前面）

class MessageStatus(models.Model):
    """记录学生是否已读通知（一对一关联 Message和 User）"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="statuses")
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="message_statuses",
        limit_choices_to={"groups__name": "Student"}
    )
    is_read = models.BooleanField(default=False, verbose_name="是否已读")
    read_time = models.DateTimeField(null=True, blank=True, verbose_name="阅读时间")

    class Meta:
        unique_together = ["message", "student"]  # 确保一个学生对一个通知只有一条状态记录
        verbose_name = "通知阅读状态"
        verbose_name_plural = "通知阅读状态"