from django.shortcuts import render
from questionManageModule.models import *
# Create your views here.
def question_view(request,question_id):
    question = Problem.objects.get(id=question_id)
    # 处理 POST 请求（表单提交）
    title = request.GET.get('title')
    content = request.GET.get('content')
    answer = request.POST.get('answer')
    attachment = request.POST.get('attachment')
    problem_type = request.GET.get('problem_type')
    difficulty = request.GET.get('difficulty')
    return render(request,'question_view_base.html')