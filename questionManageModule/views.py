from functools import wraps
from django.http import JsonResponse
from django.urls import reverse
import json,logging
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Problem, ProblemContent, Answer, ProblemType, Subject  # 确保导入所有需要的模型
logger = logging.getLogger(__name__)
def admin_required(view_func):
    """自定义装饰器：仅允许管理员（user_attribute >= 3）访问"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        if request.user.user_attribute < 3:
            print(request.user.username,'没有权限访问该页面')
            messages.error(request, "您没有权限访问该页面。")
            return redirect('question_list')  # 或重定向到首页
        return view_func(request, *args, **kwargs)
    return _wrapped_view
@login_required(login_url="login")
def question_list(request):
    """问题列表"""
    questions = Problem.objects.all()
    return render(request, 'question_list.html', {'questions': questions})
# @admin_required
@login_required(login_url="login")
def question_detail(request, question_id):
    """问题详情"""
    question = get_object_or_404(Problem, id=question_id)
    return render(request, 'question_detail.html', {'question': question})
@login_required(login_url="login")
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
@admin_required
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
@admin_required
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
@admin_required
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
@admin_required
def question_update(request, question_id):
    """更新问题及其关联的答案和内容"""
    question = get_object_or_404(Problem, id=question_id)

    # 准备GET请求时需要的数据
    problem_types = ProblemType.objects.all()
    subjects = Subject.objects.all()
    context = {
        'question': question,
        'problem_types': problem_types,
        'subjects': subjects,
    }

    if request.method == 'POST':
        # 使用数据库事务，确保所有操作要么全部成功，要么全部失败回滚
        try:
            with transaction.atomic():
                # --- 1. 更新 Problem 自身的字段 ---
                question.title = request.POST.get('title', '').strip()
                question.difficulty = request.POST.get('difficulty')
                question.estimated_time = request.POST.get('estimated_time') or 0

                # 更新外键字段时，直接赋ID值更高效
                question.problem_type_id = request.POST.get('problem_type')
                question.subject_id = request.POST.get('subject')

                # --- 2. 更新关联的 ProblemContent 对象 ---
                content_text = request.POST.get('content', '').strip()
                if question.content:
                    # 如果已存在内容对象，则更新
                    question.content.content = content_text
                    question.content.save()
                elif content_text:
                    # 如果不存在但表单提交了内容，则创建
                    new_content = ProblemContent.objects.create(content=content_text)
                    question.content = new_content

                # --- 3. 更新/创建/删除关联的 Answer 对象 ---
                answer_content = request.POST.get('answer_content', '').strip()
                answer_explanation = request.POST.get('answer_explanation', '').strip()
                answer_content_data_str = request.POST.get('answer_content_data', '').strip()

                # 验证JSON数据
                answer_data = {}
                if answer_content_data_str:
                    try:
                        answer_data = json.loads(answer_content_data_str)
                    except json.JSONDecodeError:
                        # 如果JSON格式错误，则中断并返回错误信息
                        messages.error(request, "答案数据 (JSON) 格式无效，更新失败。")
                        return render(request, 'question_update.html', context)

                # 如果有任何答案信息，则创建或更新Answer对象
                if answer_content or answer_explanation or answer_data:
                    if question.answer:
                        answer_obj = question.answer
                        answer_obj.content = answer_content
                        answer_obj.explanation = answer_explanation
                        answer_obj.content_data = answer_data
                        answer_obj.save()
                    else:
                        new_answer = Answer.objects.create(
                            content=answer_content,
                            explanation=answer_explanation,
                            content_data=answer_data
                        )
                        question.answer = new_answer
                # 如果所有答案字段都为空，则删除关联的答案
                elif question.answer:
                    question.answer.delete()
                    question.answer = None

                # --- 4. 最后，保存对 question 对象的所有修改 ---
                question.save()

        except Exception as e:
            # 捕获任何可能的异常，防止程序崩溃
            messages.error(request, f"更新过程中发生未知错误: {e}")
            return render(request, 'question_update.html', context)

        messages.success(request, f'问题 #{question.id} 更新成功')
        return redirect('question_detail', question_id=question.id)

    # 如果是GET请求，正常渲染页面
    return render(request, 'question_update.html', context)
@admin_required
def question_delete(request, question_id):
    """删除问题"""
    question = get_object_or_404(Problem, id=question_id)
    if request.method == 'POST':
        question.delete()
        messages.success(request, '问题删除成功')
        return redirect('question_list')
    return render(request, 'question_confirm_delete.html', {'question': question})

