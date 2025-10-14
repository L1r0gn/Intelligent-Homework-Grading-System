from functools import wraps

import jwt
from django.contrib.sites import requests
from django.http import JsonResponse
from django.urls import reverse
import json,logging
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from IntelligentHomeworkGradingSystem import settings
from userManageModule.decorators import jwt_login_required
from .models import Problem, ProblemContent, Answer, ProblemType, Subject, ProblemTag  # 确保导入所有需要的模型
from django.core.paginator import Paginator
from django.db.models import Q
logger = logging.getLogger(__name__)
def admin_required(view_func):
    """自定义装饰器：仅允许管理员（user_attribute >= 3）访问"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        if request.user.user_attribute < 3:
            logger.info(request.user.username,'没有权限访问该页面')
            messages.error(request, "您没有权限访问该页面。")
            return redirect('question_list')  # 或重定向到首页
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required(login_url="login")
def question_list(request):
    """问题列表（支持搜索和分页）"""
    # 优先获取相关联的对象，以优化性能
    question_queryset = Problem.objects.select_related(
        'subject', 'problem_type'
    ).prefetch_related('tags').order_by('-create_time')

    # 处理搜索请求
    search_query = request.GET.get('q', '').strip()
    if search_query:
        question_queryset = question_queryset.filter(
            Q(title__icontains=search_query) |
            Q(subject__name__icontains=search_query) |
            Q(problem_type__name__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()

    # 设置分页
    paginator = Paginator(question_queryset, 10)  # 每页显示 10 条
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'question_list.html', context)
# @admin_required
@login_required(login_url="login")
def question_detail(request, question_id):
    """问题详情"""
    question = get_object_or_404(Problem, id=question_id)
    return render(request, 'question_detail.html', {'question': question})
@jwt_login_required
@csrf_exempt
def wx_question_detail_random(request):
    """问题详情"""
    if request.method == 'GET':
        try:
            # 使用order_by('?')随机排序并获取第一条记录
            question = Problem.objects.filter(is_active=True).order_by('?').first()
            # question = Problem.objects.filter(id = 435).first()
            logger.info(question.problem_type.name)
            logger.info(question.answer)
            if question:
                # 序列化数据，确保只返回可JSON序列化的对象
                data = {
                    'id': question.id,
                    'content': question.content.content,
                    'problem_type': question.problem_type.name,
                }
                return JsonResponse({'question': data})
            else:
                return JsonResponse({'error': 'No questions available'}, status=404)
        except Exception as e:
            # 记录异常到日志，便于调试
            logger.error(f"Error in random_question view: {str(e)}")
            return JsonResponse({'error': 'Internal server error'}, status=500)
# 核心处理函数：复用的单条问题创建逻辑
def handle_problem_creation(
        title, content, difficulty, problem_type, subject,
        estimated_time, content_data, creator=None, points=0,
        answer_data=None, tags_to_add=None
):
    """
    核心功能：创建单条问题及关联的内容、答案和标签
    """
    with transaction.atomic():
        # ... (创建 ProblemContent 和 Answer 的逻辑保持不变) ...
        if not content:
            raise ValueError("题目内容(content)不能为空")
        content_obj = ProblemContent.objects.create(content=content)

        answer_obj = None
        if answer_data and answer_data.get('content'):
            answer_obj = Answer.objects.create(
                content=answer_data['content'],
                explanation=answer_data.get('explanation', '')
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
            answer=answer_obj,
            # is_active 字段会自动设为 True (模型中的默认值)
        )

        # --- 新增：为创建的问题添加标签 ---
        if tags_to_add:
            problem.tags.add(*tags_to_add)

        return problem
@admin_required
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
# 已修改：导入流程的第1步
@admin_required
def question_batch_import_json(request):
    """
    处理JSON文件的初始上传，解析文件，
    然后重定向到审核页面。
    """
    if request.method == 'POST':
        json_file = request.FILES.get('json_file')
        default_subject_id = request.POST.get('default_subject_id')
        default_problem_type_id = request.POST.get('default_problem_type_id')

        # ... (文件和参数校验部分保持不变) ...

        try:
            # ... (json.load 和类型检查部分保持不变) ...
            json_data = json.load(json_file)
            if not isinstance(json_data, list):
                raise TypeError('JSON文件顶层必须是数组格式 (e.g., [...])')

            review_items = []
            for idx, item in enumerate(json_data, start=1):
                # ... (解析 title, answer_content, category_name 等逻辑保持不变) ...
                if not item.get('question'):
                    logger.warning(f"因缺少 'question' 字段，已跳过第 {idx} 条数据。")
                    continue

                title = item.get('title')
                if not title:
                    title = f"{item.get('year', '')} {item.get('category', '')} - 题 {item.get('index', idx)}".strip()

                answer_content = item.get('answer', '')
                answer_explanation = item.get('analysis', '')
                category_name = item.get('category', '').strip()

                review_items.append({
                    'title': title,
                    'content': item.get('question', ''),
                    'difficulty': item.get('difficulty', 2),
                    'estimated_time': item.get('estimated_time', 10),
                    'points': item.get('score', 0),
                    'answer_content': answer_content,
                    'answer_explanation': answer_explanation,
                    'tags': category_name,
                    # --- 新增：将默认ID存入每一项 ---
                    'subject_id': default_subject_id,
                    'problem_type_id': default_problem_type_id,
                })

            # 现在Session中每一项都包含了它自己的科目和题型ID
            request.session['import_review_data'] = review_items
            # 这一行可以删掉或保留，新逻辑不再依赖它
            # request.session['import_defaults'] = { ... }

            messages.info(request, f'JSON文件已解析。请审核并修改以下 {len(review_items)} 条待导入题目。')
            return redirect('question_import_review')

        except (json.JSONDecodeError, TypeError) as e:
            messages.error(request, f'JSON格式错误: {e}')
        except Exception as e:
            logger.error(f'批量导入预处理失败：{str(e)}', exc_info=True)
            messages.error(request, f'处理文件时发生严重错误：{str(e)}')

        return redirect('question_batch_import_json')
    else:
        # GET 请求逻辑不变
        subjects = Subject.objects.all()
        problem_types = ProblemType.objects.all()
        return render(request, 'question_batch_import_json.html', {
            'subjects': subjects,
            'problem_types': problem_types,
        })
@admin_required
def question_import_review(request):
    """
    展示待审核的题目，并处理最终的创建请求。
    """
    review_items = request.session.get('import_review_data', [])

    if not review_items:
        messages.warning(request, '没有待审核的题目数据，请先上传文件。')
        return redirect('question_batch_import_json')

    if request.method == 'POST':
        success_count = 0
        error_items = []

        # 获取待处理题目的总数
        num_items = len(review_items)

        for i in range(num_items):
            try:
                # 根据索引从 request.POST 中解析每一道题的数据
                title = request.POST.get(f'item_{i}_title', '')
                content = request.POST.get(f'item_{i}_content', '')
                subject_id = request.POST.get(f'item_{i}_subject')
                problem_type_id = request.POST.get(f'item_{i}_problem_type')
                difficulty = request.POST.get(f'item_{i}_difficulty', 2)
                points = request.POST.get(f'item_{i}_points', 0)
                tags_str = request.POST.get(f'item_{i}_tags', '')

                answer_content = request.POST.get(f'item_{i}_answer_content', '')
                answer_explanation = request.POST.get(f'item_{i}_answer_explanation', '')

                # 准备标签数据
                tags_to_add = []
                if tags_str:
                    tag, created = ProblemTag.objects.get_or_create(name=tags_str.strip())
                    tags_to_add.append(tag)

                # 准备答案数据
                answer_data = None
                if answer_content:
                    answer_data = {
                        'content': answer_content,
                        'explanation': answer_explanation
                    }

                # 调用核心函数创建题目
                handle_problem_creation(
                    title=title,
                    content=content,
                    difficulty=difficulty,
                    problem_type=problem_type_id,
                    subject=subject_id,
                    estimated_time=10,  # 暂时写死，也可在表单中添加
                    creator=request.user if request.user.is_authenticated else None,
                    points=points,
                    answer_data=answer_data,
                    tags_to_add=tags_to_add,
                    content_data='{}'
                )
                success_count += 1
            except Exception as e:
                error_title = request.POST.get(f'item_{i}_title', f'第 {i + 1} 条数据')
                error_items.append(f"数据 '{error_title}' 导入失败: {str(e)}")
                continue

        # 处理完毕后，清理session数据
        if 'import_review_data' in request.session:
            del request.session['import_review_data']

        if success_count > 0:
            messages.success(request, f'成功导入 {success_count} 条问题。')
        if error_items:
            error_html = '<ul>' + ''.join(f'<li>{error}</li>' for error in error_items) + '</ul>'
            messages.error(request, f'导入失败 {len(error_items)} 条，详情如下：{error_html}', extra_tags='safe')

        return redirect('question_list')

    # GET请求时，需要传递所有可选的科目和题型到模板，用于生成下拉框
    else:
        all_subjects = Subject.objects.all()
        all_problem_types = ProblemType.objects.all()
        return render(request, 'question_import_review.html', {
            'review_items': review_items,
            'all_subjects': all_subjects,
            'all_problem_types': all_problem_types,
        })
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
                question.title = request.POST.get('title', '').strip()
                question.difficulty = request.POST.get('difficulty')
                question.estimated_time = request.POST.get('estimated_time') or 0
                problem_type_id = request.POST.get('problem_type')
                question.subject_id = request.POST.get('subject')
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

                if problem_type_id:
                    try:
                        # 使用 ID 从数据库中查找对应的 ProblemType 对象
                        problem_type_instance = ProblemType.objects.get(id=problem_type_id)
                        # 3. 将获取到的对象实例赋给 question 的外键字段
                        question.problem_type = problem_type_instance
                    except ProblemType.DoesNotExist:
                        # 如果传入的 ID 无效，可以进行错误处理，例如返回一个错误响应
                        # 这里我们简单地将其设置为 None，或者你可以根据业务逻辑决定如何处理
                        question.problem_type = None
                else:
                    question.problem_type = None

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
@admin_required
def question_batch_action(request):
    """处理批量操作的视图（删除、禁用、启用）"""
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_ids')

        if not action:
            messages.error(request, '未选择任何操作！')
            return redirect('question_list')

        if not selected_ids:
            messages.error(request, '未选择任何问题！')
            return redirect('question_list')

        # 将ID转换为整数
        selected_ids = [int(id) for id in selected_ids]

        # 获取所有选中的问题对象
        queryset = Problem.objects.filter(pk__in=selected_ids)

        if action == 'delete':
            count, _ = queryset.delete()
            messages.success(request, f'成功删除了 {count} 个问题。')

        elif action == 'disable':
            count = queryset.update(is_active=False)
            messages.success(request, f'成功禁用了 {count} 个问题。')

        elif action == 'enable':
            count = queryset.update(is_active=True)
            messages.success(request, f'成功启用了 {count} 个问题。')

        else:
            messages.warning(request, '无效的操作。')

    return redirect('question_list')
@admin_required
@require_http_methods(["POST"])
def ajax_create_subject(request):
    """处理创建新科目的AJAX请求"""
    return _ajax_create_model_instance(request, Subject, '科目')
@admin_required
@require_http_methods(["POST"])
def ajax_create_problem_type(request):
    """处理创建新题型的AJAX请求"""
    return _ajax_create_model_instance(request, ProblemType, '题型')

def _ajax_create_model_instance(request, model_class, model_name_singular):
    """
    通用辅助函数：通过AJAX创建一个模型实例（例如 Subject 或 ProblemType）。
    - request: Django request对象。
    - model_class: 要创建的模型类 (e.g., Subject).
    - model_name_singular: 模型的单数名称，用于错误消息 (e.g., '科目').
    """
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()

        if not name:
            return JsonResponse({'error': f'{model_name_singular}名称不能为空。'}, status=400)

        if model_class.objects.filter(name=name).exists():
            return JsonResponse({'error': f'{model_name_singular} "{name}" 已存在。'}, status=400)

        new_instance = model_class.objects.create(name=name)
        return JsonResponse({'id': new_instance.id, 'name': new_instance.name}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON数据。'}, status=400)
    except Exception as e:
        logger.error(f'AJAX创建{model_name_singular}失败: {str(e)}', exc_info=True)
        return JsonResponse({'error': '服务器内部错误。'}, status=500)
