from statistics import quantiles

from django.db import transaction
from django.http import JsonResponse
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

def wx_question_detail_random(request):
    """问题详情"""
    if request.method == 'GET':
        try:
            # 使用order_by('?')随机排序并获取第一条记录
            question = Problem.objects.order_by('?').first()
            print(question.problem_type.name)
            print(question.answer)
            if question:
                # 序列化数据，确保只返回可JSON序列化的对象
                data = {
                    'id': question.id,
                    'content': question.content.content,
                    
                }
                return JsonResponse({'question': data})
            else:
                return JsonResponse({'error': 'No questions available'}, status=404)
        except Exception as e:
            # 记录异常到日志，便于调试
            logger.error(f"Error in random_question view: {str(e)}")
            return JsonResponse({'error': 'Internal server error'}, status=500)

# 1. 核心处理函数：复用的单条问题创建逻辑
def handle_problem_creation(
        title, content, difficulty, problem_type, subject,
        estimated_time, content_data, creator=None, points=0,
        answer_data=None
):
    """
    核心功能：创建单条问题及关联的内容和答案
    忽略：得分点、附件、标签
    """
    with transaction.atomic():
        # 创建题目内容（ProblemContent）
        if not content:
            raise ValueError("内容为空")
        try:
            content_data_parsed = json.loads(content_data) if content_data else {}
        except json.JSONDecodeError:
            content_data_parsed = {}
        content_obj = ProblemContent.objects.create(
            content=content,
            content_data=content_data_parsed
        )

        # 创建答案（Answer）- 可选
        answer_obj = None
        if answer_data and answer_data.get('content'):
            try:
                answer_content_data = json.loads(answer_data.get('content_data', '{}'))
            except json.JSONDecodeError:
                answer_content_data = {}
            answer_obj = Answer.objects.create(
                content=answer_data['content'],
                explanation=answer_data.get('explanation', ''),
                content_data=answer_content_data
            )

        # 创建问题主体（Problem）
        problem = Problem.objects.create(
            title=title,
            content=content_obj,
            problem_type_id=problem_type,
            difficulty=difficulty,
            subject_id=subject,
            estimated_time=estimated_time,
            creator=creator,
            points=points,
            answer=answer_obj
        )

        return problem


# 2. 原单条创建函数：调用核心处理函数
def question_create(request):
    # 设置默认值
    title = ''
    content = ''
    difficulty = ''
    problem_type = None
    subject = None
    estimated_time = 10  # 设置默认值
    existing_questions = Problem.objects.all()  # 显示全部问题
    if request.method == 'POST':
        try:
            # 从POST获取参数
            title = request.POST.get('title')
            difficulty = request.POST.get('difficulty')
            problem_type = request.POST.get('problem_type')
            subject = request.POST.get('subject')
            estimated_time = request.POST.get('estimated_time')
            content_data = request.POST.get('content_data', '{}')
            points = request.POST.get('points', 0)

            # 处理答案数据（如果表单有相关字段）
            answer_data = {
                'content': request.POST.get('answer_content', ''),
                'explanation': request.POST.get('answer_explanation', ''),
                'content_data': request.POST.get('answer_content_data', '{}')
            }

            # 调用核心函数创建
            handle_problem_creation(
                title=title,
                content=content,
                difficulty=difficulty,
                problem_type=problem_type,
                subject=subject,
                estimated_time=estimated_time,
                content_data=content_data,
                creator=request.user if request.user.is_authenticated else None,
                points=points,
                answer_data=answer_data if answer_data['content'] else None
            )

            messages.success(request, '问题创建成功')
            return redirect('question_list')


        except Exception as e:
            logger.error('问题创建失败:%s', str(e), exc_info=True)
            messages.error(request, f'创建失败: {str(e)}')
            # 保持上下文返回表单
            return render(request, 'question_update.html', {
                'title': title,
                'content': content,
                'difficulty': difficulty,
                'problem_type': problem_type,
                'subject': subject,
                'estimated_time': estimated_time,
                'problem_types': ProblemType.objects.all(),
                'subjects': Subject.objects.all(),
                'existing_questions': existing_questions,  # 新增：传递已有问题列表
            })
    # GET请求渲染表单
    return render(request, 'question_create.html', {
        'title': title,
        'content': content,
        'difficulty': difficulty,
        'problem_type': problem_type,
        'subject': subject,
        'estimated_time': estimated_time,
        'problem_types': ProblemType.objects.all(),
        'subjects': Subject.objects.all(),
        'existing_questions': existing_questions,  # 新增：传递已有问题列表到模板
    })


# 3. 批量导入函数：调用核心处理函数
def question_batch_import_json(request):
    if request.method == 'POST':
        json_file = request.FILES.get('json_file')
        if not json_file or not json_file.name.endswith('.json'):
            messages.error(request, '请上传.json格式的文件')
            return render(request, 'question_batch_import_json.html')

        try:
            # 读取并解析JSON
            json_data = json.load(json_file)
            if not isinstance(json_data, list):
                messages.error(request, 'JSON必须是数组格式（每条数据对应一道题）')
                return render(request, 'question_batch_import_json.html')

            success_count = 0
            error_items = []

            # 循环处理每条数据
            for idx, item in enumerate(json_data, start=1):
                try:
                    # 调用核心函数创建单条问题
                    handle_problem_creation(
                        title=item.get('title', ''),
                        content=item.get('content', ''),
                        difficulty=item.get('difficulty', ''),
                        problem_type=item.get('problem_type_id'),
                        subject=item.get('subject_id'),
                        estimated_time=item.get('estimated_time', 10),
                        content_data=item.get('content_data', '{}'),
                        creator=request.user if request.user.is_authenticated else None,
                        points=item.get('points', 0),
                        answer_data=item.get('answer')  # 从JSON获取答案数据
                    )
                    success_count += 1
                except Exception as e:
                    error_items.append(f"第{idx}条：{str(e)}")
                    continue

            # 反馈结果
            if success_count > 0:
                messages.success(request, f'成功导入{success_count}条问题')
            if error_items:
                messages.error(request, f'导入失败{len(error_items)}条：\n' + '\n'.join(error_items))
            return redirect('question_list')

        except json.JSONDecodeError:
            messages.error(request, 'JSON格式错误，请检查文件内容')
        except Exception as e:
            logger.error(f'批量导入失败：{str(e)}', exc_info=True)
            messages.error(request, f'导入失败：{str(e)}')

    # GET请求显示导入页面
    return render(request, 'question_batch_import_json.html')


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

