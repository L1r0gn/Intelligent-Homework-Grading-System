# serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Assignment, AssignmentStatus, className
from questionManageModule.models import ProblemType, Subject, ProblemTag

class AssignmentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    class_name = serializers.CharField(source='target_class.class_name', read_only=True)
    problem_title = serializers.CharField(source='problem.title', read_only=True)

    class Meta:
        model = Assignment
        # 显式列出所有字段，并加入 problem 和 problem_title
        fields = [
            'id', 'title', 'description', 'teacher', 'teacher_name',
            'target_class', 'class_name', 'created_at', 'deadline',
            'attachment', 'problem', 'problem_title'
        ]
        read_only_fields = ('id', 'created_at', 'teacher', 'teacher_name', 'class_name', 'problem_title')

class AssignmentStatusSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_id = serializers.CharField(source='student.userprofile.student_id', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    problem_id = serializers.IntegerField(source='assignment.problem.id', read_only=True)

    class Meta:
        model = AssignmentStatus
        # 显式列出所有字段，特别是新增的答案、分数、反馈字段
        fields = [
            'id', 'assignment', 'assignment_title', 'problem_id',
            'student', 'student_name',
            'status', 'submitted_at',

            # --- 以下是核心修改 ---
            'answer_content',  # 学生提交的文本答案
            'answer_data',  # 学生提交的JSON答案 (如选择题)
            'score',  # 批改后的得分
            'feedback'  # 教师或AI的反馈
        ]

        # 'score' 和 'feedback' 理论上只有教师或批改系统能修改
        # 但在API中，学生提交时需要写入 'answer_content' 和 'answer_data'
        # 这需要您在视图(View)中单独处理权限
        # 这里我们先把它们都暴露出来

class ProblemTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemType
        fields = ['id', 'name', 'code', 'description', 'is_active']

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code', 'description']

class ProblemTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemTag
        fields = ['id', 'name', 'description', 'color']