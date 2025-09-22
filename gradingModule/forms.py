# gradingModule/forms.py
from django import forms


class SubmissionFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', '所有状态'),
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('graded', '已评分'),
        ('error', '错误'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label='状态筛选'
    )

    assignment = forms.CharField(
        required=False,
        label='作业名称',
        widget=forms.TextInput(attrs={'placeholder': '输入作业名称'})
    )

    student = forms.CharField(
        required=False,
        label='学生姓名',
        widget=forms.TextInput(attrs={'placeholder': '输入学生姓名'})
    )