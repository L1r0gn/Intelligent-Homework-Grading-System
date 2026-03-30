from functools import wraps
from django.http import JsonResponse
from django.urls import reverse
import json, logging
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from questionManageModule.models import  StudentMastery
from userManageModule.decorators import jwt_login_required
# 确保导入 KnowledgePoint
from .models import Problem, ProblemContent, Answer, ProblemType, Subject, ProblemTag, KnowledgePoint
from dkt_app.recommendation_utils import get_user_mastery_probabilities
import numpy as np

logger = logging.getLogger(__name__)


def admin_required(view_func):
    """自定义装饰器：仅允许管理员（user_attribute >= 3）访问"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        if request.user.user_attribute < 3:
            messages.error(request, "您没有权限访问该页面。")
            return redirect('question_list')
        return view_func(request, *args, **kwargs)

    return _wrapped_view


# ==========================================
# 1. 知识点管理视图 (新增)
# ==========================================

@admin_required
def knowledge_point_list(request):
    """知识点列表管理"""
    kps = KnowledgePoint.objects.select_related('subject').all().order_by('subject', 'name')

    # 简单的搜索
    query = request.GET.get('q', '')
    if query:
        kps = kps.filter(Q(name__icontains=query) | Q(subject__name__icontains=query))

    paginator = Paginator(kps, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'knowledge_point_list.html', {
        'page_obj': page_obj,
        'search_query': query
    })


@admin_required
def knowledge_point_create(request):
    """创建知识点"""
    if request.method == 'POST':
        name = request.POST.get('name')
        subject_id = request.POST.get('subject')
        description = request.POST.get('description', '')

        if name and subject_id:
            KnowledgePoint.objects.create(name=name, subject_id=subject_id, description=description)
            messages.success(request, '知识点创建成功')
            return redirect('knowledge_point_list')
        else:
            messages.error(request, '名称和所属科目不能为空')

    subjects = Subject.objects.all()
    return render(request, 'knowledge_point_form.html', {'subjects': subjects, 'action': '创建'})


@admin_required
def knowledge_point_update(request, kp_id):
    """编辑知识点"""
    kp = get_object_or_404(KnowledgePoint, id=kp_id)
    if request.method == 'POST':
        kp.name = request.POST.get('name')
        kp.subject_id = request.POST.get('subject')
        kp.description = request.POST.get('description', '')
        kp.save()
        messages.success(request, '知识点更新成功')
        return redirect('knowledge_point_list')

    subjects = Subject.objects.all()
    return render(request, 'knowledge_point_form.html', {'kp': kp, 'subjects': subjects, 'action': '编辑'})


@admin_required
def knowledge_point_delete(request, kp_id):
    """删除知识点"""
    kp = get_object_or_404(KnowledgePoint, id=kp_id)
    if request.method == 'POST':
        kp.delete()
        messages.success(request, '知识点已删除')
    return redirect('knowledge_point_list')


# ==========================================
# 2. 现有的问题视图 (已修改以支持知识点)
# ==========================================

@login_required(login_url="login")
def question_list(request):
    """问题列表"""
    # 增加 prefetch_related('knowledge_points') 以优化查询
    question_queryset = Problem.objects.select_related(
        'subject', 'problem_type'
    ).prefetch_related('tags', 'knowledge_points').order_by('-create_time')

    # 获取所有可用的筛选选项
    all_subjects = Subject.objects.all()
    all_types = ProblemType.objects.all()
    # 难度选项直接使用模型中的 choices
    difficulty_choices = Problem.DIF_CHOICES

    # --- 筛选逻辑 ---
    search_query = request.GET.get('q', '').strip()
    subject_id = request.GET.get('subject')
    type_id = request.GET.get('type')
    difficulty_val = request.GET.get('difficulty')

    if search_query:
        question_queryset = question_queryset.filter(
            Q(title__icontains=search_query) |
            Q(content__content__icontains=search_query) | # 同时也搜内容
            Q(tags__name__icontains=search_query) |
            Q(knowledge_points__name__icontains=search_query)
        ).distinct()

    if subject_id:
        question_queryset = question_queryset.filter(subject_id=subject_id)
    
    if type_id:
        question_queryset = question_queryset.filter(problem_type_id=type_id)
        
    if difficulty_val:
        question_queryset = question_queryset.filter(difficulty=difficulty_val)

    paginator = Paginator(question_queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'all_subjects': all_subjects,
        'all_types': all_types,
        'difficulty_choices': difficulty_choices,
        # 回显当前选中的值
        'current_subject': int(subject_id) if subject_id else None,
        'current_type': int(type_id) if type_id else None,
        'current_difficulty': int(difficulty_val) if difficulty_val else None,
    }
    return render(request, 'question_list.html', context)


@login_required(login_url="login")
def question_detail(request, question_id):
    question = get_object_or_404(Problem, id=question_id)
    return render(request, 'question_detail.html', {'question': question})


def handle_problem_creation(
        title, content, difficulty, problem_type, subject,
        estimated_time, content_data, creator=None, points=0,
        answer_data=None, tags_to_add=None, knowledge_point_ids=None  # 新增参数
):
    with transaction.atomic():
        if not content:
            raise ValueError("题目内容(content)不能为空")
        content_obj = ProblemContent.objects.create(content=content)

        answer_obj = None
        if answer_data and answer_data.get('content'):
            answer_obj = Answer.objects.create(
                content=answer_data['content'],
                explanation=answer_data.get('explanation', '')
            )

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
        )

        if tags_to_add:
            problem.tags.add(*tags_to_add)

        # --- 新增：关联知识点 ---
        if knowledge_point_ids:
            problem.knowledge_points.set(knowledge_point_ids)

        return problem


@admin_required
def question_create(request):
    # 默认值
    context = {
        'problem_types': ProblemType.objects.all(),
        'subjects': Subject.objects.all(),
        'knowledge_points': KnowledgePoint.objects.all().order_by('subject'),  # 传递所有知识点
        'existing_questions': Problem.objects.all()
    }

    if request.method == 'POST':
        try:
            # 基础字段
            title = request.POST.get('title')
            difficulty = request.POST.get('difficulty')
            problem_type = request.POST.get('problem_type')
            subject = request.POST.get('subject')
            estimated_time = request.POST.get('estimated_time')
            content = request.POST.get('content')  # 注意：这里要获取 content
            content_data = request.POST.get('content_data', '{}')
            points = request.POST.get('points', 0)

            # 获取选中的知识点 ID 列表
            kp_ids = request.POST.getlist('knowledge_points')

            answer_data = {
                'content': request.POST.get('answer_content', ''),
                'explanation': request.POST.get('answer_explanation', ''),
                'content_data': request.POST.get('answer_content_data', '{}')
            }

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
                answer_data=answer_data if answer_data['content'] else None,
                knowledge_point_ids=kp_ids  # 传递知识点
            )

            messages.success(request, '问题创建成功')
            return redirect('question_list')

        except Exception as e:
            logger.error('问题创建失败:%s', str(e), exc_info=True)
            messages.error(request, f'创建失败: {str(e)}')
            context.update(request.POST.dict())  # 回填表单数据
            return render(request, 'question_update.html', context)  # 注意：这里如果失败可能需要专门的 create 模板或者复用 update

    return render(request, 'question_create.html', context)


@admin_required
def question_update(request, question_id):
    question = get_object_or_404(Problem, id=question_id)

    # 准备上下文
    problem_types = ProblemType.objects.all()
    subjects = Subject.objects.all()
    all_kps = KnowledgePoint.objects.all().order_by('subject')  # 所有知识点

    # 获取当前题目已选的知识点ID，用于前端回显
    selected_kp_ids = list(question.knowledge_points.values_list('id', flat=True))

    context = {
        'question': question,
        'problem_types': problem_types,
        'subjects': subjects,
        'knowledge_points': all_kps,
        'selected_kp_ids': selected_kp_ids
    }

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 基础信息更新
                question.title = request.POST.get('title', '').strip()
                question.difficulty = request.POST.get('difficulty')
                question.points = request.POST.get('points', 0)
                question.estimated_time = request.POST.get('estimated_time') or 0
                question.subject_id = request.POST.get('subject')

                # 题型更新
                problem_type_id = request.POST.get('problem_type')
                if problem_type_id:
                    question.problem_type_id = problem_type_id
                else:
                    question.problem_type = None

                # 内容更新
                content_text = request.POST.get('content', '').strip()
                if question.content:
                    question.content.content = content_text
                    question.content.save()
                elif content_text:
                    new_content = ProblemContent.objects.create(content=content_text)
                    question.content = new_content

                # --- 知识点更新 (核心修改) ---
                kp_ids = request.POST.getlist('knowledge_points')
                question.knowledge_points.set(kp_ids)  # 自动处理增删

                # 答案更新
                answer_content = request.POST.get('answer_content', '').strip()
                answer_explanation = request.POST.get('answer_explanation', '').strip()
                answer_content_data_str = request.POST.get('answer_content_data', '').strip()

                answer_data = {}
                if answer_content_data_str:
                    try:
                        answer_data = json.loads(answer_content_data_str)
                    except json.JSONDecodeError:
                        messages.error(request, "答案数据 JSON 格式无效")
                        return render(request, 'question_update.html', context)

                if answer_content or answer_explanation or answer_data:
                    if question.answer:
                        ans = question.answer
                        ans.content = answer_content
                        ans.explanation = answer_explanation
                        ans.content_data = answer_data
                        ans.save()
                    else:
                        new_ans = Answer.objects.create(content=answer_content, explanation=answer_explanation,
                                                        content_data=answer_data)
                        question.answer = new_ans
                elif question.answer:
                    question.answer.delete()
                    question.answer = None

                question.save()

            messages.success(request, f'问题 #{question.id} 更新成功')
            return redirect('question_detail', question_id=question.id)

        except Exception as e:
            logger.error(f"更新错误: {e}")
            messages.error(request, f"更新过程中发生错误: {e}")
            return render(request, 'question_update.html', context)

    return render(request, 'question_update.html', context)


# ... (question_delete, question_batch_action, import 等其他函数保持不变) ...
# 请保留你原文件中其他的 helper 函数和 import view
@admin_required
def question_delete(request, question_id):
    question = get_object_or_404(Problem, id=question_id)
    if request.method == 'POST':
        question.delete()
        messages.success(request, '问题删除成功')
        return redirect('question_list')
    return render(request, 'question_confirm_delete.html', {'question': question})


@admin_required
def question_batch_action(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_ids')
        if not action or not selected_ids:
            return redirect('question_list')

        queryset = Problem.objects.filter(pk__in=selected_ids)
        if action == 'delete':
            queryset.delete()
        elif action == 'disable':
            queryset.update(is_active=False)
        elif action == 'enable':
            queryset.update(is_active=True)

    return redirect('question_list')


# 剩下的 AJAX 和 Import 函数请直接保留原样，无需修改
@jwt_login_required
@csrf_exempt
def wx_question_detail_random(request):
    """问题详情"""
    if request.method == 'GET':
        try:
            # logger.info("进入 wx_question_detail_random 视图。")
            user = request.user
            logger.info(f"当前用户ID: {user.id}，发起了随机问题请求")

            mastery_probs_raw = get_user_mastery_probabilities(user)
            # test
            # logger.info(f"用户 {user.id} 的原始知识点掌握度: {mastery_probs_raw}")


            # 方案三 + 方案二 组合推荐逻辑
            mastery_threshold_T = 0.7  # 掌握度上限
            alpha = 0.7  # 平滑因子

            eligible_kps_with_mastery = {}
            for kp, mastery in mastery_probs_raw.items():
                if mastery < mastery_threshold_T:
                    eligible_kps_with_mastery[kp] = mastery
            
            # logger.info(f"用户 {user.id} 掌握度低于 {mastery_threshold_T} 的知识点: {[(kp.name, mastery) for kp, mastery in eligible_kps_with_mastery.items()]}")

            if not eligible_kps_with_mastery:
                logger.info(f"用户 {user.id} 没有掌握度低于 {mastery_threshold_T} 的知识点，进行随机推荐。")
                # Fallback to pure random if no weak知识点
                question = Problem.objects.filter(is_active=True).order_by('?').first()
                if question:
                    logger.info(f"为用户 {user.id} 随机推荐了题目: {question.id} ({question.problem_type.name})")
                    data = {
                        'id': question.id,
                        'content': question.content.content if question.content else '',
                        'problem_type': question.problem_type.name if question.problem_type else '',
                    }
                    return JsonResponse({'question': data})
                else:
                    logger.warning(f"用户 {user.id} 随机推荐失败，没有可用题目。")
                    return JsonResponse({'error': 'No questions available'}, status=404)

            # 计算推荐概率 (方案二)
            knowledge_points = list(eligible_kps_with_mastery.keys())
            weaknesses = np.array([1 - mastery for mastery in eligible_kps_with_mastery.values()])
            
            # 避免所有弱点都为0导致除以零，或者所有弱点相同导致概率计算问题
            if np.all(weaknesses == 0):
                selection_probabilities = np.ones(len(weaknesses)) / len(weaknesses)
                # logger.info(f"所有薄弱点掌握度相同，平均分配推荐概率。")
            else:
                weighted_weaknesses = weaknesses ** alpha
                selection_probabilities = weighted_weaknesses / np.sum(weighted_weaknesses)
            
            # logger.info(f"用户 {user.id} 知识点薄弱度: {[(kp.name, w) for kp, w in zip(knowledge_points, weaknesses)]}")
            # logger.info(f"用户 {user.id} 知识点推荐概率: {[(kp.name, p) for kp, p in zip(knowledge_points, selection_probabilities)]}")

            selected_question = None
            max_attempts = 5  # 尝试从薄弱知识点中选择问题的次数
            attempts = 0

            while selected_question is None and attempts < max_attempts:
                attempts += 1
                try:
                    # 随机选择一个知识点
                    chosen_kp = np.random.choice(knowledge_points, p=selection_probabilities)
                    logger.info(f"尝试 {attempts}/{max_attempts}: 选中知识点 '{chosen_kp.name}' (掌握度: {eligible_kps_with_mastery[chosen_kp]:.2f})。")
                    
                    # 查找与该知识点关联的题目
                    # 确保题目是激活的，并且至少有一个知识点与 chosen_kp 匹配
                    candidate_questions = Problem.objects.filter(
                        is_active=True,
                        knowledge_points=chosen_kp
                    ).order_by('?') # 可以在这些题目中再随机一个

                    if candidate_questions.exists():
                        selected_question = candidate_questions.first()
                        logger.info(f"成功为用户 {user.id} 推荐了基于薄弱知识点 '{chosen_kp.name}' 的题目: {selected_question.id}.")
                    else:
                        logger.warning(f"知识点 '{chosen_kp.name}' 没有找到可用题目，尝试重新选择。")
                except ValueError as ve:
                    logger.error(f"选择知识点或题目时发生ValueError: {ve}")
                    break # Break if probabilities are messed up

            if selected_question:
                logger.info(f"最终为用户 {user.id} 推荐了题目: {selected_question.id} ({selected_question.problem_type.name})。")
                data = {
                    'id': selected_question.id,
                    'content': selected_question.content.content if selected_question.content else '',
                    'problem_type': selected_question.problem_type.name if selected_question.problem_type else '',
                }
                return JsonResponse({'question': data})
            else:
                logger.warning(f"经过 {max_attempts} 次尝试，未能为用户 {user.id} 找到基于薄弱知识点的题目。最终进行随机推荐。")
                # 最终 fallback 到纯随机推荐
                question = Problem.objects.filter(is_active=True).order_by('?').first()
                if question:
                    logger.info(f"最终 fallback: 为用户 {user.id} 随机推荐了题目: {question.id} ({question.problem_type.name})")
                    data = {
                        'id': question.id,
                        'content': question.content.content if question.content else '',
                        'problem_type': question.problem_type.name if question.problem_type else '',
                    }
                    return JsonResponse({'question': data})
                else:
                    logger.warning(f"最终 fallback 失败: 用户 {user.id} 没有可用题目。")
                    return JsonResponse({'error': 'No questions available'}, status=404)

        except Exception as e:
            # 记录异常到日志，便于调试
            logger.error(f"Error in random_question view: {e}")
            return JsonResponse({'error': 'Internal server error'}, status=500)


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


@jwt_login_required
def wx_search_questions(request):
    """
    微信端：搜索题目接口
    支持参数：
    - keyword: 搜索标题、内容
    - kp_id: 知识点ID
    - page: 分页
    """
    keyword = request.GET.get('keyword', '').strip()
    kp_id = request.GET.get('kp_id')

    # 只查询激活的题目
    questions = Problem.objects.filter(is_active=True).select_related('problem_type', 'subject')

    # 按知识点筛选
    if kp_id:
        questions = questions.filter(knowledge_points__id=kp_id)

    # 按关键词筛选（同时搜标题、内容、知识点名称）
    if keyword:
        questions = questions.filter(
            Q(title__icontains=keyword) |
            Q(content__content__icontains=keyword) |
            Q(knowledge_points__name__icontains=keyword)
        ).distinct()

    # 默认按时间倒序，限制返回数量防止数据量过大
    total_count = questions.count()
    questions = questions.order_by('-create_time')[:50]

    data = []
    for q in questions:
        # 获取该题关联的知识点名称
        kp_names = [kp.name for kp in q.knowledge_points.all()[:3]]

        data.append({
            'id': q.id,
            'title': q.title if q.title else f'题目 #{q.id}',
            'problem_type': q.problem_type.name,
            'difficulty': q.get_difficulty_display(),
            'knowledge_points': kp_names,
            'subject': q.subject.name,
            # 截取一部分内容作为预览
            'content_preview': q.content.content[:40] + '...' if q.content else ''
        })

    return JsonResponse({'success': True, 'data': data, 'total': total_count})


@jwt_login_required
def wx_get_question_by_id(request, question_id):
    """
    微信端：获取指定ID的题目详情 (用于精准练习)
    """
    try:
        question = Problem.objects.get(id=question_id, is_active=True)

        # 构造与 random 接口一致的数据结构
        data = {
            'id': question.id,
            'content': question.content.content,
            'problem_type': question.problem_type.name,
            'points': question.points,
            'difficulty': question.get_difficulty_display(),
            'answer': question.answer.content,
            'analysis': question.answer.explanation,
            # 你可以根据需要添加更多字段
        }
        return JsonResponse({'success': True, 'question': data})
    except Problem.DoesNotExist:
        return JsonResponse({'success': False, 'error': '题目不存在或已下架'}, status=404)


@jwt_login_required
def wx_get_student_stats(request):
    """微信端：获取学生的学习统计数据 (能力画像)"""
    student = request.user

    # 1. 获取基础统计
    # 总做题数 (已批改的提交)
    from gradingModule.models import Submission
    total_submissions = Submission.objects.filter(
        student=student,
        status__in=['GRADED', 'ACCEPTED', 'WRONG_ANSWER']
    ).count()

    # 2. 获取知识点掌握度列表
    stats_list = []

    if StudentMastery:
        # 查询该学生的所有掌握度记录，按分数降序排列
        mastery_records = StudentMastery.objects.filter(
            student=student
        ).select_related('knowledge_point').order_by('-mastery_level')

        logger.info(f"发送的所有知识点掌握记录为{mastery_records}")

        for record in mastery_records:
            stats_list.append({
                'id': record.knowledge_point.id,
                'name': record.knowledge_point.name,
                'score': round(record.mastery_level, 1),  # 保留1位小数
                'score_percent': int((record.mastery_level / 5.0) * 100),  # 用于前端进度条宽度
                'count': record.total_questions_attempted if hasattr(record, 'total_questions_attempted') else 0
            })

    # 计算平均能力值
    avg_score = 0
    if stats_list:
        total_score = sum(item['score'] for item in stats_list)
        avg_score = round(total_score / len(stats_list), 1)
    logger.info(f"发送的用户的能力值数据为{stats_list}")
    return JsonResponse({
        'success': True,
        'data': {
            'total_questions': total_submissions,
            'avg_mastery': avg_score,
            'stats_list': stats_list
        }
    })
