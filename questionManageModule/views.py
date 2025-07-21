from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import *


def question_list(request):
    """问题列表"""
    questions = Problem.objects.all()
    return render(request, 'question_list.html', {'questions': questions})

def question_detail(request, question_id):
    """问题详情"""
    question = get_object_or_404(Problem, id=question_id)
    return render(request, 'question_detail.html', {'question': question})


def question_create(request):
    if request.method == 'POST':
        try:
            # 新增内容处理
            content_obj = ProblemContent.objects.create(
                content=request.POST['content'],
                content_data={}
            )

            problem_data = {
                'title': request.POST['title'],
                'content': content_obj,  # 关联内容对象
                'difficulty': request.POST.get('difficulty', 2),
                'problem_type_id': request.POST['problem_type'],
                'subject_id': request.POST['subject'],
                'points': request.POST.get('points', 0),
                'creator': request.user
            }

            # 增加字段验证
            required_fields = ['title', 'content', 'problem_type', 'subject']
            for field in required_fields:
                if not request.POST.get(field):
                    raise ValueError(f'必填字段 {field} 不能为空')

            question = Problem.objects.create(**problem_data)

            # 事务处理多对多关系
            with transaction.atomic():
                if tags := request.POST.getlist('tags'):
                    question.tags.add(*Tag.objects.filter(id__in=tags))

                # 处理附件上传
                for file in request.FILES.getlist('attachments'):
                    ProblemAttachment.objects.create(
                        problem=question,
                        file=file,
                        name=file.name
                    )

            messages.success(request, '问题创建成功')
            return redirect('question_detail', question_id=question.id)

        except Exception as e:
            messages.error(request, f'创建失败: {str(e)}')
            # 回滚已创建的内容对象
            if 'content_obj' in locals():
                content_obj.delete()

    # 保持现有上下文准备
    return render(request, 'question_form.html', {
        'problem_types': ProblemType.objects.all(),
        'subjects': Subject.objects.all(),
        'tags': ProblemTag.objects.all()
    })

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