from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from pyexpat.errors import messages

from userManageModule.models import User
from .forms import SubmissionFilterForm
from .models import Submission, Problem
from .tasks import process_and_grade_submission # 导入你的异步任务
import json
@csrf_exempt
def submissionprocess(request):
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
        # 1. 解码并用 json.loads() 解析 request.body
        data = json.loads(request.body.decode('utf-8'))

        # 2. 从解析后的 data 字典中获取数据
        problem_id = data.get('questionId')
        submitted_text = data.get('submitted_text')
        choose_answer = data.get('selectedAnswer')
        userId = data.get('userId')

        if not problem_id:
            return HttpResponseBadRequest("请求必须包含 'problem_id' ")
        # if not submitted_image:
        #     return HttpResponseBadRequest("请求必须包含 'submitted_image' ")
        # if not submitted_text:
        #     return HttpResponseBadRequest("请求必须包含 'submitted_text' ")
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return JsonResponse({'error': '指定的题目不存在'}, status=404)
        user = User.objects.get(id=userId)
        print('用户',user,"创建了新提交")
        if not user:
            return HttpResponseBadRequest({'error':'用户不存在'},status=405)
        # 创建新的 submission 实例，保存图片
        submission = Submission.objects.create(
            student=user,
            problem=problem,
            submitted_text=submitted_text,
            choose_answer=choose_answer,
            # submitted_image=submitted_image,
            status='PENDING', # 初始状态为判题中
        )
        submissions = Submission.objects.filter(student=user).order_by('-submitted_time')
        print(submissions)
        # 触发异步任务！使用 .delay() 方法，任务会被发送到 Celery 队列中等待执行
        process_and_grade_submission.delay(submission.id)
        # 立即返回响应给用户
        response_data = {
            'id': submission.id,
            'message': '提交成功，正在判题中...',
            'status': submission.status
        }
        return JsonResponse(response_data, status=201)
    else:
        return JsonResponse({'error': '不支持的请求方法'}, status=405)
@login_required(login_url="login")
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
@login_required(login_url="login")
def submission_detail(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    # 检查权限：教师可以查看所有，学生只能查看自己的
    if not request.user.is_staff and submission.student != request.user:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("您没有权限查看此提交")

    context = {
        'submission': submission,
    }

    return render(request, 'submission_detail.html', context)
@login_required
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
        print(submission,'is regrading')
        print(submission.id)
        # --- 这里是核心：调用您已有的Celery异步任务 ---
        process_and_grade_submission.delay(submission.id)
        # 将用户重定向回作业详情页
        return redirect('submission_list')
    # 如果是GET或其他方法的请求，直接重定向走，不处理
    return redirect('submission_list')