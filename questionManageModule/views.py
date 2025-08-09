from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import *
import json,logging
logger = logging.getLogger(__name__)


def question_list(request):
    """问题列表"""
    questions = Problem.objects.all()
    return render(request, 'question_list.html', {'questions': questions})

def question_detail(request, question_id):
    """问题详情"""
    question = get_object_or_404(Problem, id=question_id)
    return render(request, 'question_detail.html', {'question': question})


def question_create(request):
    title = ''
    content = ''
    difficulty = ''
    problem_type = None
    subject = None
    estimated_time = 10  # 设置默认值
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 处理POST请求
                title = request.POST.get('title')
                content = request.POST.get('content')
                difficulty = request.POST.get('difficulty')
                problem_type = request.POST.get('problem_type')
                subject = request.POST.get('subject')
                estimated_time = request.POST.get('estimated_time')

                if not content:
                    messages.error(request, '问题内容不能为空')
                    raise ValueError("内容为空")  # ✅ 触发事务回滚
                # 新增富文本内容处理（添加JSON解析异常处理）
                try:
                    content_data = json.loads(request.POST.get('content_data', '{}'))
                except json.JSONDecodeError:
                    content_data = {}

                # 后创建关联内容
                content_obj = ProblemContent.objects.create(
                    problem=None,
                    content=content,
                    content_data=content_data
                )
                problem = Problem.objects.create(
                    title=title,
                    content=content_obj,
                    difficulty=difficulty,
                    problem_type_id=problem_type,
                    subject_id=subject,
                    estimated_time=estimated_time,
                )
                problem.save()
                content_obj.problem = problem
                content_obj.save()

                messages.success(request, '问题创建成功')
                return redirect('question_list')

        except Exception as e:
            logger.error('问题创建失败:%s',str(e),exc_info=True)
            messages.error(request, f'创建失败: {str(e)}')
            # 保持现有上下文准备
            return render(request, 'question_update.html', {
                'title': title,
                'content': content,
                'difficulty': difficulty,
                'problem_type': problem_type,
                'subject': subject,
                'estimated_time': estimated_time,
                'problem_types': ProblemType.objects.all(),
                'subjects': Subject.objects.all(),
            })
        # GET 请求
    return render(request, 'question_create.html', {
        'title': title,
        'content': content,
        'difficulty': difficulty,
        'problem_type': problem_type,
        'subject': subject,
        'estimated_time': estimated_time,
        'problem_types': ProblemType.objects.all(),
        'subjects': Subject.objects.all(),
    })

def question_update(request, question_id):
    """更新问题"""
    question = get_object_or_404(Problem, id=question_id)
    if request.method == 'POST':
        # 处理更新逻辑
        messages.success(request, '问题更新成功')
        return redirect('question_detail', question_id=question.id)
    return render(request, 'question_update.html', {
        'question': question,
        'problem_types': ProblemType.objects.all(),
        'subjects': Subject.objects.all(),
    })

def question_delete(request, question_id):
    """删除问题"""
    question = get_object_or_404(Problem, id=question_id)
    if request.method == 'POST':
        question.delete()
        messages.success(request, '问题删除成功')
        return redirect('question_list')
    return render(request, 'question_confirm_delete.html', {'question': question})