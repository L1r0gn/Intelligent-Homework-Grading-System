from audioop import reverse
from datetime import timezone
from functools import wraps
from http.client import responses

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest, Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

from userManageModule.decorators import jwt_login_required
from userManageModule.models import User
from .forms import SubmissionFilterForm
from .models import Submission, Problem
from .tasks import process_and_grade_submission # 导入你的异步任务
import json
from  IntelligentHomeworkGradingSystem.views import logger
def admin_required(view_func):
    """自定义装饰器：仅允许管理员（user_attribute >= 3）访问"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_attribute < 3:
            logger.info("%s 的权限等级为 %s",request.user.username, request.user.user_attribute)
            logger.info("%s 没有权限访问该页面", request.user.username)
            messages.error(request, "您没有权限访问该页面。")
            return redirect('question_list')  # 或重定向到首页
        return view_func(request, *args, **kwargs)
    return _wrapped_view
@csrf_exempt
@jwt_login_required
def submissionprocess(request):
    """
    处理提交请求，包括异步处理和返回结果
    Args:
        request (HttpRequest): Django HTTP 请求对象
    Returns:
        JsonResponse: 包含提交信息的 JSON 响应
    """
    if request.method == 'GET':
        # GET 请求逻辑保持不变
        user = request.user
        submissions = Submission.objects.filter(student=user).order_by('-submitted_time')
        data = []
        for sub in submissions:
            data.append({
                'id': sub.id,
                'problem_id': sub.problem.id,
                'problem_type': sub.problem.problem_type,
                'student_username': sub.student.username,
                'status': sub.get_status_display(), # 使用 get_xxx_display() 获取更友好的状态名
                'score': sub.score,
                'justification': sub.justification, # 返回评分理由
                'submitted_time': sub.submitted_time.strftime('%Y-%m-%d %H:%M:%S'),
            })
        return JsonResponse(data, safe=False)
    elif request.method == 'POST':
        # 1. 解析json数据
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return HttpResponseBadRequest("JSON 解析错误")
        else:
            # 当使用 wx.uploadFile 时，参数会在这里
            data = request.POST

        # 2. 从解析后的 data 字典中获取数据
        submitted_text = data.get('submitted_text')
        problem_id = data.get('questionId')
        choose_answer = data.get('selectedAnswer')  # 用于选择题
        userId = data.get('userId')
        submitted_image = request.FILES.get('submitted_image')  # 用于主观题

        ### important - decide use assignment/question ###
        source = data.get('from')
        if not source:
            return HttpResponseBadRequest("请求必须包含 'from'")

        if not problem_id:
            return HttpResponseBadRequest("请求必须包含 'problem_id'")
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return JsonResponse({'error': '指定的题目不存在'}, status=404)

        try:
            user = User.objects.get(id=userId)
        except User.DoesNotExist:
            return HttpResponseBadRequest('用户不存在')
        logger.info(f"用户 {user.wx_nickName}创建了新提交")

        from django.utils import timezone
        # 创建新的 submission 实例，保存图片
        submission = Submission.objects.create(
            problem=problem,
            student=user,
            submitted_text=submitted_text,
            submitted_time=timezone.now(),
            submitted_image=submitted_image,
            choose_answer=choose_answer,
            status='PENDING', # 初始状态为判题中
            score=0,
            feedback='',
            justification='',
        )
        if source == 'assignment':
            assignment_id = data.get('assignment_id')
            if not assignment_id:
                return HttpResponseBadRequest("请求必须包含 'assignment_id'")
            from assignmentAndClassModule.models import AssignmentStatus,Assignment
            assignment=Assignment.objects.get(id=assignment_id)
            assignment_status,created = AssignmentStatus.objects.get_or_create(
                assignment=assignment,
                submission=submission,
                student=user,
                defaults={
                    'submitted_at': timezone.now(),
                    # 其他需要的默认字段
                }
            )
            assignment_status.save()
        elif source == 'question':
            submission.save()
        ### test
        submissions = Submission.objects.filter(student=user).order_by('-submitted_time')
        logger.info("用户 %s 当前共有 %d 条提交记录", user.wx_nickName, submissions.count())
        ### end test

        # 触发异步任务！使用 .delay() 方法，任务会被发送到 Celery 队列中等待执行
        process_and_grade_submission.delay(submission_id=submission.id)


        # 立即返回响应给用户
        response_data = {
            'id': submission.id,
            'message': '提交成功，正在判题中...',
            # 'status': submission.status
        }
        return JsonResponse(response_data, status=200)
    else:
        return JsonResponse({'error': '不支持的请求方法'}, status=405)
@admin_required
def submission_list(request):
    # 获取所有提交记录，按时间倒序排列
    submissions = Submission.objects.all().order_by('-submitted_time')
    # 初始化筛选表单
    form = SubmissionFilterForm(request.GET or None)
    # 应用筛选
    if form.is_valid():
        status = form.cleaned_data.get('status')
        assignment = form.cleaned_data.get('assignment')
        student = form.cleaned_data.get('student')

        if status:
            submissions = submissions.filter(status=status)
        if assignment:
            submissions = submissions.filter(assignment__title__icontains=assignment)
        if student:
            submissions = submissions.filter(student__username__icontains=student)

    # 分页
    paginator = Paginator(submissions, 25)  # 每页25条记录
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'form': form,
        'total_count': submissions.count(),
    }

    return render(request, 'submission_list.html', context)
@admin_required
def submission_detail(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    context = {
        'submission': submission,
    }

    return render(request, 'submission_detail.html', context)
@admin_required
def regrade_submission_view(request, submission_id):
    """处理重新批改作业的视图函数"""
    # 我们只处理POST请求
    if request.method == 'POST':
        # 安全地获取指定的提交对象，如果不存在则会返回404错误
        submission = get_object_or_404(Submission, pk=submission_id)
        # (推荐) 在重新提交任务前，可以先重置一下状态
        submission.status = 'PENDING'  # 例如，重置为“待处理”
        submission.score = None  # 清空之前的分数
        submission.grading_result = "正在重新加入批改队列..."
        submission.save()
        logger.info("%s is regrading", submission)
        logger.info("Regrading submission ID: %s", submission.id)
        # --- 这里是核心：调用您已有的Celery异步任务 ---
        process_and_grade_submission.delay(submission_id=submission.id)
        # 将用户重定向回作业详情页
        return redirect('submission_list')
    # 如果是GET或其他方法的请求，直接重定向走，不处理
    return redirect('submission_list')

def serve_submission_image(request, submission_id):
    try:
        submission = Submission.objects.get(id=submission_id)
    except Submission.DoesNotExist:
        raise Http404("Image not found")

    response = HttpResponse(
        submission.submitted_image,
        content_type='image/jpeg'
    )
    response['Content-Disposition'] = 'inline'  # 在浏览器中直接显示，而非下载
    return response


@jwt_login_required
def showMySubmissions(request):
    """
    获取当前登录用户的所有提交记录。
    支持分页、筛选、排序功能，并可限制返回的记录数量。

    请求方法:
        GET

    参数:
        - page (int, optional): 当前页码，默认为 1。必须大于 0。
        - limit (int, optional): 每页返回的记录数，默认为 20。必须在 1 到 100 之间。
        - offset (int, optional): 偏移量，用于计算分页。如果同时提供 page 和 offset，page 优先。
        - querycounts (int, optional): 限制返回的记录总数。如果提供，将只返回前 querycounts 条记录，
                                       忽略分页参数 (page, limit, offset)。必须是正整数。
        - sort_by (str, optional): 排序字段和顺序，格式为 "字段:顺序"。
                                   支持字段: 'submitted_time', 'score', 'created_at' (同 submitted_time)。
                                   支持顺序: 'desc' (降序, 默认), 'asc' (升序)。
                                   例如: "submitted_time:desc"。
        - filter_by (str, optional): 筛选条件，格式为 "字段:值"。
                                    支持字段: 'status', 'question_type', 'problem_id'。
                                    例如: "status:ACCEPTED"。
        - user_id (int, optional): 用于管理员查询其他用户的提交记录。非管理员用户尝试查询他人记录将返回权限错误。

    返回:
        JsonResponse: 包含提交记录列表、总数、当前页、每页限制和是否有更多记录。
                      示例:
                      {
                          "data": [
                              {
                                  "record_id": 1,
                                  "question_id": 101,
                                  "question_title": "数学题1",
                                  "user_answer": "...",
                                  "is_correct": true,
                                  "score": 100,
                                  "status": "ACCEPTED",
                                  "created_at": "2023-01-01 10:00:00"
                              }
                          ],
                          "total_count": 50,
                          "page": 1,
                          "limit": 20,
                          "has_more": true
                      }

    错误响应:
        - 400 Bad Request: 参数校验失败 (e.g., page < 1, limit out of range, invalid querycounts)。
        - 403 Forbidden: 非管理员用户尝试查询其他用户提交记录。
        - 405 Method Not Allowed: 非 GET 请求。
        - 404 Not Found: (当 user_id 指定的用户不存在时)
        - 500 Internal Server Error: 服务器内部错误。
    """
    if request.method != "GET":
        return HttpResponseBadRequest("Method Not Allowed")

    try:
        # 1. 获取并校验分页参数
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0)) # 支持offset，但优先使用page逻辑
        
        # 兼容处理：如果提供了offset但没有page，我们依然基于limit计算切片
        # 但通常建议使用 page/limit 模式或 offset/limit 模式之一
        
        if page < 1:
            return JsonResponse({'error': 'Page must be greater than 0'}, status=400)
        if limit < 1 or limit > 100:
            return JsonResponse({'error': 'Limit must be between 1 and 100'}, status=400)
        if offset < 0:
            return JsonResponse({'error': 'Offset must be non-negative'}, status=400)

        # === 新增：处理 querycounts 参数 ===
        query_counts_str = request.GET.get('querycounts')
        query_counts = None
        if query_counts_str:
            try:
                query_counts = int(query_counts_str)
                if query_counts < 1:
                    return JsonResponse({'error': 'querycounts must be a positive integer'}, status=400)
            except ValueError:
                return JsonResponse({'error': 'Invalid querycounts parameter. Must be an integer.'}, status=400)
        # ==================================

        # 2. 获取筛选和排序参数
        sort_by = request.GET.get('sort_by', 'submitted_time:desc')
        filter_by = request.GET.get('filter_by') # 格式例如 "status:ACCEPTED"
        user_id = request.GET.get('user_id')

        # 3. 构建基础查询集
        # 默认查询当前登录用户的记录
        target_user = request.user
        
        # 如果指定了 user_id 且不是当前用户，检查权限 (这里简单处理：仅允许管理员查询他人)
        if user_id and str(user_id) != str(request.user.id):
            if request.user.user_attribute >= 3: # 假设 >=3 是管理员
                 target_user = get_object_or_404(User, id=user_id)
            else:
                 return JsonResponse({'error': 'Permission denied'}, status=403)

        queryset = Submission.objects.filter(student=target_user)

        # 4. 应用过滤
        if filter_by:
            try:
                filter_key, filter_value = filter_by.split(':')
                # 映射允许过滤的字段，防止任意字段查询的安全风险
                allowed_filters = {
                    'status': 'status',
                    'question_type': 'problem__problem_type__name', # 假设关联路径
                    'problem_id': 'problem__id'
                }
                
                if filter_key in allowed_filters:
                    # 对于关联字段，可能需要根据实际模型调整
                    db_field = allowed_filters[filter_key]
                    queryset = queryset.filter(**{db_field: filter_value})
            except ValueError:
                pass # 忽略格式错误的筛选条件

        # 5. 应用排序
        if sort_by:
            try:
                sort_field, sort_order = sort_by.split(':')
                allowed_sorts = {
                    'created_at': 'submitted_time',
                    'score': 'score',
                    'submitted_time': 'submitted_time'
                }
                
                if sort_field in allowed_sorts:
                    db_sort_field = allowed_sorts[sort_field]
                    if sort_order.lower() == 'desc':
                        db_sort_field = '-' + db_sort_field
                    queryset = queryset.order_by(db_sort_field)
            except ValueError:
                queryset = queryset.order_by('-submitted_time') # 默认排序
        else:
             queryset = queryset.order_by('-submitted_time')

        # === 新增：应用 query_counts 限制 ===
        if query_counts is not None:
            queryset = queryset[:query_counts]
        # ==================================

        # 6. 计算分页
        total_count = queryset.count()
        
        # 使用 Paginator 处理分页
        paginator = Paginator(queryset, limit)
        
        # 如果传入了 offset，则计算对应的 page
        if request.GET.get('offset') is not None:
             page = (offset // limit) + 1
        
        try:
            current_page = paginator.page(page)
        except Exception:
            # 如果页码超出范围，返回空列表或最后一页，这里选择返回空列表
            return JsonResponse({
                'data': [],
                'total_count': total_count,
                'page': page,
                'limit': limit,
                'has_more': False
            })

        # 7. 序列化数据
        # 关联查询 problem 以获取题目名称
        submissions_data = []
        for sub in current_page.object_list:
            submissions_data.append({
                'record_id': sub.id,
                'question_id': sub.problem.id,
                'question_title': sub.problem.title,
                'user_answer': sub.submitted_text or sub.choose_answer or (sub.submitted_image.url if sub.submitted_image else ""),
                'is_correct': sub.status == 'ACCEPTED', # 假设 ACCEPTED 为正确
                'student_score':sub.score,
                'question_score':sub.problem.points,
                'score': sub.score,
                'status': sub.status, # 补充返回具体状态
                'created_at': sub.submitted_time.strftime('%Y-%m-%d %H:%M:%S')
            })

        response_data = {
            'data': submissions_data,
            'total_count': total_count,
            'page': page,
            'limit': limit,
            'has_more': current_page.has_next()
        }

        return JsonResponse(response_data)

    except ValueError:
        return JsonResponse({'error': 'Invalid parameters'}, status=400)
    except Exception as e:
        logger.error(f"Error in showMySubmissions: {str(e)}")
        return JsonResponse({'error': 'Internal Server Error'}, status=500)
@jwt_login_required
def getASubmission(request, submission_id):
    try:
        # 获取对应的提交记录
        submission = Submission.objects.get(id=submission_id)
        if submission.submitted_image:
            image_url = request.build_absolute_uri(submission.submitted_image.url)
        else:
            image_url = None
        # 提取需要的字段
        data = {
            "problem_title": submission.problem.title,
            "submitted_time": submission.submitted_time.strftime("%Y-%m-%d %H:%M:%S"),
            "submitted_image": image_url,
            "status": submission.status,
            "score": submission.score,
            "feedback": submission.feedback,
            "justification": submission.justification,
            "choose_answer": submission.choose_answer,
            "submitted_text": submission.submitted_text,
            "problem_type": submission.problem.problem_type.name,
        }
        # 返回JSON格式的数据
        return JsonResponse(data)
    except Submission.DoesNotExist:
        # 如果提交记录不存在，返回错误信息
        return JsonResponse({"error": "Submission not found"}, status=404)

@admin_required
def submission_batch_action(request):
    """处理提交记录的批量操作"""
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_ids')
        
        if not action or not selected_ids:
            messages.error(request, "请选择要操作的记录和操作类型")
            return redirect('submission_list')

        try:
            # 获取选中的提交记录
            queryset = Submission.objects.filter(pk__in=selected_ids)
            selected_count = queryset.count()
            
            if action == 'regrade':
                # 批量重新批改
                for submission in queryset:
                    # 重置状态为待处理
                    submission.status = 'PENDING'
                    submission.score = None
                    submission.grading_result = "正在重新加入批改队列..."
                    submission.save()
                    # 调用异步任务重新批改
                    process_and_grade_submission.delay(submission_id=submission.id)
                
                messages.success(request, f'已成功将 {selected_count} 个提交记录加入重新批改队列')
                logger.info(f"批量重新批改 {selected_count} 个提交记录: {selected_ids}")
                
            elif action == 'delete':
                # 批量删除
                deleted_count = queryset.count()
                queryset.delete()
                messages.success(request, f'已成功删除 {deleted_count} 个提交记录')
                logger.info(f"批量删除 {deleted_count} 个提交记录: {selected_ids}")
                
            else:
                messages.error(request, "不支持的操作类型")
                
        except Exception as e:
            logger.error(f"批量操作失败: {str(e)}")
            messages.error(request, f"批量操作失败: {str(e)}")
    
    return redirect('submission_list')

def getSubmissionsByAssignmentId(request, assignment_id):
    try:
        # 根据assignment_id获取相关的提交记录
        # 正确的方法是通过AssignmentStatus表连接Assignment和Submission
        from assignmentAndClassModule.models import AssignmentStatus, Assignment
        
        # 获取所有与该作业相关的AssignmentStatus记录
        assignment_statuses = AssignmentStatus.objects.filter(assignment_id=assignment_id).select_related('submission')
        
        # 提取相关的提交记录
        data = []
        for assignment_status in assignment_statuses:
            submission = assignment_status.submission
            if submission:  # 确保submission存在
                if submission.submitted_image:
                    image_url = request.build_absolute_uri(submission.submitted_image.url)
                else:
                    image_url = None
                data.append({
                    "record_id": submission.id,
                    "problem_title": submission.problem.title,
                    "submitted_time": submission.submitted_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "submitted_image": image_url,
                    "status": submission.status,
                    "score": submission.score,
                    "feedback": submission.feedback,
                    "justification": submission.justification,
                    "choose_answer": submission.choose_answer,
                    "submitted_text": submission.submitted_text,
                    "problem_type": submission.problem.problem_type.name,
                    "student_name": submission.student.wx_nickName or submission.student.username,  # 添加学生姓名
                })
        
        # 返回JSON格式的数据
        return JsonResponse(data, safe=False)
    # 如果提交记录不存在，返回错误信息
    except Assignment.DoesNotExist:
        return JsonResponse({"error": "Assignment not found"}, status=404)
    except AssignmentStatus.DoesNotExist:
        return JsonResponse({"error": "No submissions found for this assignment"}, status=404)
    # 处理异常
    except Exception as e:
        logger.error(f"Error in getSubmissionsByAssignmentId: {str(e)}")
        return JsonResponse({"error": "Internal Server Error"}, status=500)
