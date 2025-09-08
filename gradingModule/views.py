from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Submission
from .serializers import SubmissionSerializer

class SubmissionListCreateAPIView(generics.ListCreateAPIView):
    """处理提交记录的列表查看(GET)和新建(POST)"""
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]  # 确保用户已登录
    def getSubmissionSet(self):
        """
        这个视图只返回当前登录用户的提交记录。
        """
        user = self.request.user
        return Submission.objects.filter(student=user)
    def createSubmission(self, serializer):
        """
        在创建新的提交记录时，自动将 `student` 字段设置为当前登录用户。
        """
        instance = serializer.save(student=self.request.user)
        # ----------- 触发智能批改的关键点 ----------- #
        # 在这里，你可以调用一个异步任务来处理批改逻辑
        # 例如: from .tasks import grade_submission
        # grade_submission.delay(instance.id)
        # ------------------------------------------- #
        print(f"新的提交记录已创建(ID: {instance.id})，等待批改...")