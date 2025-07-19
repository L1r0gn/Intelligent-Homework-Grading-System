from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Problem, Answer

def question_list(request):
    """问题列表"""
    questions = Problem.objects.all()
    return render(request, 'question_list.html', {'questions': questions})

def question_detail(request, question_id):
    """问题详情"""
    question = get_object_or_404(Problem, id=question_id)
    return render(request, 'question_detail.html', {'question': question})

def question_create(request):
    """创建问题"""
    if request.method == 'POST':
        # 处理表单提交
        title = request.POST.get('title')
        content = request.POST.get('content')
        # 创建问题逻辑
        messages.success(request, '问题创建成功')
        return redirect('question_list')
    return render(request, 'question_form.html')

def question_update(request, question_id):
    """更新问题"""
    question = get_object_or_404(Problem, id=question_id)
    if request.method == 'POST':
        # 处理更新逻辑
        messages.success(request, '问题更新成功')
        return redirect('question_detail', question_id=question.id)
    return render(request, 'question_form.html', {'question': question})

def question_delete(request, question_id):
    """删除问题"""
    question = get_object_or_404(Problem, id=question_id)
    if request.method == 'POST':
        question.delete()
        messages.success(request, '问题删除成功')
        return redirect('question_list')
    return render(request, 'question_confirm_delete.html', {'question': question})