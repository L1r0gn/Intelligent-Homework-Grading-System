from rest_framework import serializers
from .models import Submission, Problem


class SubmissionSerializer(serializers.ModelSerializer):
    # 使用PrimaryKeyRelatedField，这样在创建时只需要传递 problem 的 id
    problem = serializers.PrimaryKeyRelatedField(queryset=Problem.objects.all())

    # 将 student 字段设置为只读，因为我们会根据当前登录用户自动设置
    student = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Submission
        # fields = '__all__' # 显示所有字段
        # 或者更好地，指定需要的字段
        fields = ['id', 'problem', 'student', 'submitted_text', 'submitted_time', 'status', 'score', 'feedback']

        # 将结果字段设置为只读，防止用户在提交时直接修改分数和状态
        read_only_fields = ['id', 'student', 'submitted_time', 'status', 'score', 'feedback']