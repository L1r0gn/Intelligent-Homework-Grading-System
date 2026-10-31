# gradingModule/forms.py
from django import forms

from .models import Submission


class SubmissionFilterForm(forms.Form):
    """后台「提交记录」筛选表单。

    状态的候选项必须直接来自 Submission.STATUS_CHOICES——
    过去这里另写了一套小写取值（pending/processing/graded/error），
    和模型里的枚举完全对不上，导致筛选永远命中 0 条。

    「作业」字段实际过滤的是题目名称：提交记录直连题目（problem），
    与作业的关联要绕经 AssignmentStatus，后台列表展示的也是题目名，
    保持筛选口径与展示口径一致。
    """

    STATUS_CHOICES = [('', '所有状态')] + Submission.STATUS_CHOICES

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label='批改状态',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    problem = forms.CharField(
        required=False,
        label='题目名称',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入题目名称'}),
    )

    student = forms.CharField(
        required=False,
        label='学生姓名',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入学生姓名'}),
    )
