from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Submission, Problem
from .tasks import process_and_grade_submission # 导入你的异步任务

@login_required
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
        # POST 请求逻辑完全改变，以处理图片上传和触发异步任务
        problem_id = request.POST.get('problem_id')
        submitted_image = request.FILES.get('submitted_image')
        submitted_text = request.POST.get('submitted_text')

        if not problem_id:
            return HttpResponseBadRequest("请求必须包含 'problem_id' ")
        if not problem_id or not submitted_image:
            return HttpResponseBadRequest("请求必须包含 'problem_id' 和 'submitted_image'")
        if not problem_id or not submitted_image:
            return HttpResponseBadRequest("请求必须包含 'problem_id' 和 'submitted_image'")
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return JsonResponse({'error': '指定的题目不存在'}, status=404)

        # 创建新的 submission 实例，保存图片
        submission = Submission.objects.create(
            student=request.user,
            problem=problem,
            submitted_image=submitted_image,
            status='PENDING' # 初始状态为判题中
        )
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