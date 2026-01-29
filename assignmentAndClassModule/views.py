# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.db import transaction
from django.utils import timezone
from gradingModule.models import Submission
from gradingModule.tasks import process_and_grade_submission
from gradingModule.views import logger
# === 修改点 1：确保导入 KnowledgePoint ===
from questionManageModule.models import (
    ProblemType, Subject, ProblemTag,
    Problem, ProblemContent, Answer, KnowledgePoint
)
from rest_framework import status
from rest_framework.response import Response

from userManageModule.decorators import jwt_login_required
from .models import Assignment, className, AssignmentStatus


@api_view(['POST'])
@jwt_login_required
@csrf_exempt
@transaction.atomic  # --- 使用事务确保数据一致性 ---
def push_assignment(request):
    """
    老师发布新作业。

    功能描述:
        该视图允许教师（已认证）通过一个请求同时完成“创建新题目”和“将该题目作为作业发布给指定班级”两个操作。
        它在一个数据库事务中处理所有逻辑，确保数据的一致性。

    Args:
        request (Request): DRF的Request对象，包含以下字段:
            - class_id (int): 目标班级的ID。
            - title (str): 作业和题目的标题。
            - description (str, optional): 作业的描述。
            - deadline (str): 作业截止日期 (e.g., "YYYY-MM-DDTHH:MM:SSZ")。
            - content (str): 题目内容。
            - problem_type (int): 题目类型ID。
            - subject (int): 科目ID。
            - difficulty (int): 难度系数。
            - tags (list[int], optional): 题目标签ID列表。
            - knowledge_points (list[int], optional): 关联的知识点ID列表。
            - estimated_time (int, optional): 预计完成时间（分钟）。
            - points (int): 题目分值。
            - answer (str): 标准答案。
            - explanation (str, optional): 答案解析。

    Returns:
        Response:
            - 成功 (HTTP 200 OK): 返回包含作业ID和题目ID的成功信息。
            - 失败 (HTTP 400/500): 返回具体的错误原因，如班级不存在、数据校验失败等。
    """
    if request.method == 'POST':
        teacher = request.user
        data = request.data

        # --- 1. 从 data 中提取数据 ---
        class_id = data.get('class_id')

        # 作业信息
        assignment_title = data.get('title')  # 作业标题 (前端复用了'title')
        assignment_description = data.get('description')  # 作业描述 (前端可能没有，用题目内容代替)
        deadline = data.get('deadline')  # 假设前端会传来 deadline

        # 题目信息
        problem_content_text = data.get('content')
        problem_type_id = data.get('problem_type')
        subject_id = data.get('subject')
        difficulty = data.get('difficulty')
        tag_ids = data.get('tags', [])  # 标签ID列表
        # === 修改点 2：接收前端传来的知识点 ID 列表 ===
        knowledge_point_ids = data.get('knowledge_points', [])

        estimated_time = data.get('estimated_time')
        points = data.get('points')

        # 答案和解析信息
        answer_text = data.get('answer')
        explanation_text = data.get('explanation')

        # --- 2. 验证并获取关联对象 ---
        try:
            target_class = className.objects.get(id=class_id)
            problem_type = ProblemType.objects.get(id=problem_type_id)
            subject = Subject.objects.get(id=subject_id)

            # --- 3. 创建 Problem 及其依赖项 ---

            # 3.1 创建答案 (Answer)
            answer_obj = Answer.objects.create(
                content=answer_text,
                explanation=explanation_text
            )

            # 3.2 创建题目内容 (ProblemContent)
            problem_content_obj = ProblemContent.objects.create(
                content=problem_content_text
            )

            # 3.3 创建题目 (Problem)
            new_problem = Problem.objects.create(
                title=assignment_title,  # 我们复用作业标题作为题目标题
                content=problem_content_obj,
                problem_type=problem_type,
                creator=teacher,
                difficulty=difficulty,
                subject=subject,
                points=points,
                answer=answer_obj,
                estimated_time=estimated_time
            )

            # 3.4 关联 题目标签 (Tags)
            if tag_ids:
                tags = ProblemTag.objects.filter(id__in=tag_ids)
                new_problem.tags.set(tags)

            # === 修改点 3：关联 知识点 (Knowledge Points) ===
            if knowledge_point_ids:
                # 这一步会自动处理多对多关系
                new_problem.knowledge_points.set(knowledge_point_ids)

            # --- 4. 创建 作业 (Assignment) ---
            assignment = Assignment.objects.create(
                teacher=teacher,
                target_class=target_class,
                title=assignment_title,  # 作业标题
                description=assignment_description or problem_content_text,  # 描述
                deadline=deadline,
                problem=new_problem  # --- 核心：关联刚创建的题目 ---
            )

            # --- 5. 为学生创建状态 (AssignmentStatus) ---
            students = target_class.members.all()
            status_list = []
            for student in students:
                status_list.append(
                    AssignmentStatus(
                        assignment=assignment,
                        student=student
                        # submission 字段在学生提交作业时再设置
                    )
                )
            AssignmentStatus.objects.bulk_create(status_list)  # 批量创建，效率更高

            return Response({
                'success': True,
                'assignment_id': assignment.id,
                'problem_id': new_problem.id,
                'message': '作业发布成功，知识点已关联'
            })

        except className.DoesNotExist:
            return Response({'success': False, 'error': '班级不存在'}, status=status.HTTP_400_BAD_REQUEST)
        except ProblemType.DoesNotExist:
            return Response({'success': False, 'error': '题目类型不存在'}, status=status.HTTP_400_BAD_REQUEST)
        except Subject.DoesNotExist:
            return Response({'success': False, 'error': '科目不存在'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # 捕获其他未知错误
            logger.error(f"创建作业失败: {str(e)}")
            return Response({'success': False, 'error': f'创建失败: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- 其他视图保持不变 ---

@jwt_login_required
def student_assignments(request):
    """
    学生获取自己的作业列表。

    功能描述:
        该视图供学生（已认证）调用，返回其所有已加入班级的作业列表。
        可以根据请求头中的 'ClassId' 筛选特定班级的作业。
        同时，会附带每份作业的当前状态（如待完成、已提交、已批改等）。

    Args:
        request (Request): DRF的Request对象。
            - Headers (optional): {'ClassId': '班级ID'} 用于筛选特定班级的作业。

    Returns:
        JsonResponse:
            - 成功 (HTTP 200 OK): 返回一个包含作业列表的JSON对象。
              每个作业对象都包含详细信息及提交状态。
    """
    student = request.user
    student_classes = student.class_in.all()

    if not student_classes.exists():
        return JsonResponse({
            'success': True,
            'data': [],
            'message': '您还没有加入任何班级'
        })

    assignments = Assignment.objects.filter(
        target_class__in=student_classes
    ).select_related('teacher', 'target_class', 'problem').order_by('-created_at')

    class_id = request.headers.get('ClassId')
    if class_id:
        assignments = assignments.filter(target_class__id=class_id)

    assignments_data = []
    for assignment in assignments:
        assignmentStatusOfThisAssignment = assignment.assignmentstatus_set.filter(assignment=assignment).first()
        if assignmentStatusOfThisAssignment and assignmentStatusOfThisAssignment.submission:
            assignment_status = assignmentStatusOfThisAssignment.submission.status
            submitted_at = assignmentStatusOfThisAssignment.submitted_at.strftime(
                '%Y-%m-%d %H:%M') if assignmentStatusOfThisAssignment.submitted_at else None
        else:
            assignment_status = 'PENDING'
            submitted_at = None

        assignments_data.append({
            'id': assignment.id,
            'title': assignment.title,
            'description': assignment.description,
            'teacher_name': assignment.teacher.wx_nickName or assignment.teacher.username,
            'class_name': assignment.target_class.name,
            'created_at': assignment.created_at.strftime('%Y-%m-%d %H:%M'),
            'deadline': assignment.deadline.strftime('%Y-%m-%d %H:%M') if assignment.deadline else None,
            'problem_id': assignment.problem.id if assignment.problem else None,
            'problem_title': assignment.problem.title if assignment.problem else '传统作业',
            'status': assignment_status,
            'status_text': {
                'PENDING': '待完成',
                'SUBMITTED': '已提交',
                'GRADED': '已批改',
                'WRONG_ANSWER': '答案错误',
                'ACCEPTED': '答案正确',  # 修正拼写 ACCEPT -> ACCEPTED
            }.get(assignment_status, '未知'),
            'submitted_at': submitted_at,
        })
    return JsonResponse({
        'success': True,
        'data': assignments_data
    })


@jwt_login_required
def teacher_get_assignments(request, class_id):
    """
    老师获取指定班级的作业列表。

    功能描述:
        该视图供教师（已认证）调用，返回其在特定班级（由class_id指定）发布的所有作业列表。

    Args:
        request (Request): DRF的Request对象。
        class_id (int): 目标班级的ID。

    Returns:
        JsonResponse:
            - 成功 (HTTP 200 OK): 返回一个包含作业列表的JSON对象。
    """
    if request.method == 'GET':
        teacher = request.user
        assignments = Assignment.objects.filter(teacher=teacher, target_class__id=class_id).order_by('-created_at')
        return_assignments = []
        for assignment in assignments:
            return_assignments.append({
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'teacher_name': assignment.teacher.wx_nickName,
                'class_name': assignment.target_class.name,
                'created_at': assignment.created_at.strftime('%Y-%m-%d %H:%M'),
                'deadline': assignment.deadline.strftime('%Y-%m-%d %H:%M') if assignment.deadline else None,
                'problem_id': assignment.problem.id if assignment.problem else None,
                'problem_title': assignment.problem.title if assignment.problem else '传统作业 (仅附件)',
            })
        return JsonResponse({'data': return_assignments})


@jwt_login_required
def problem_meta_data(request):
    """
    获取创建题目所需的元数据。

    功能描述:
        该视图为前端提供创建新题目时所需的各种下拉选项数据，
        包括题目类型、科目、标签以及所有知识点。

    Args:
        request (Request): DRF的Request对象。

    Returns:
        JsonResponse:
            - 成功 (HTTP 200 OK): 返回一个包含problemTypes, subjects, tags, knowledgePoints列表的JSON对象。
            - 失败 (HTTP 500): 如果查询过程中发生错误。
    """
    try:
        problem_types = ProblemType.objects.filter(is_active=True).values('id', 'name', 'code')
        subjects = Subject.objects.all().values('id', 'name', 'code')
        tags = ProblemTag.objects.all().values('id', 'name', 'color')

        # === 修改点 4：返回所有知识点 ===
        # 前端可以根据 subjects[i].id 来过滤显示的知识点，或者在这里直接按科目分组返回
        # 这里为了通用，返回所有，并带上 subject_id
        knowledge_points = KnowledgePoint.objects.all().values('id', 'name', 'subject_id')

        return JsonResponse({
            'success': True,
            'data': {
                'problemTypes': list(problem_types),
                'subjects': list(subjects),
                'tags': list(tags),
                'knowledgePoints': list(knowledge_points)  # 新增
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@jwt_login_required
def get_student_homework_detail(request, assignment_id):
    """
    学生获取单份作业的详细信息。

    功能描述:
        该视图供学生（已认证）调用，用于在做题页面加载特定作业的详细内容。
        它会返回作业信息、题目详情，以及学生过往的提交记录（如果存在）。

    Args:
        request (Request): DRF的Request对象。
        assignment_id (int): 目标作业的ID。

    Returns:
        JsonResponse:
            - 成功 (HTTP 200 OK): 返回包含作业和题目详细信息的JSON对象。
            - 失败 (HTTP 404 NOT FOUND): 如果作业不存在。
            - 失败 (HTTP 403 FORBIDDEN): 如果学生不属于该作业对应的班级。
    """
    student = request.user
    try:
        assignment = Assignment.objects.select_related(
            'teacher', 'target_class', 'problem', 'problem__problem_type'
        ).get(id=assignment_id)
    except Assignment.DoesNotExist:
        return JsonResponse({'success': False, 'error': '作业不存在'}, status=404)

    if not student.class_in.filter(id=assignment.target_class.id).exists():
        return JsonResponse({'success': False, 'error': '您不是该班级成员，无法查看此作业'}, status=403)

    status_obj, created = AssignmentStatus.objects.get_or_create(
        assignment=assignment,
        student=student,
        defaults={'status': 'pending'}
    )

    problem = assignment.problem
    if status_obj.submission:
        status = status_obj.submission.status
        score = status_obj.submission.score
    else:
        status = 'pending'
        score = 0

    data = {
        'assignment_id': assignment.id,
        'assignment_title': assignment.title,
        'teacher_name': assignment.teacher.wx_nickName or assignment.teacher.username,
        'deadline': assignment.deadline.strftime('%Y-%m-%d %H:%M') if assignment.deadline else None,
        'assignment_status_id': status_obj.id,
        'status': status,
        'score': score,
        'submitted_at': status_obj.submitted_at.strftime('%Y-%m-%d %H:%M') if status_obj.submitted_at else None,
    }

    if status_obj.submission:
        data.update({
            'submission_id': status_obj.submission.id,
            'submission_image': status_obj.submission.submitted_image.url if status_obj.submission.submitted_image else None,
            'submission_text': status_obj.submission.submitted_text,
            'ai_justification': status_obj.submission.justification,  # AI 评语
            'choose_answer': status_obj.submission.choose_answer
        })

    if problem:
        problem_content_text = ""
        if hasattr(problem, 'content') and problem.content:
            problem_content_text = problem.content.content

        data.update({
            'problem_id': problem.id,
            'problem_title': problem.title,
            'problem_points': problem.points,
            'problem_type': problem.problem_type.name,
            'problem_type_code': problem.problem_type.code if problem.problem_type else '',
            'problem_content': problem_content_text,
            'standard_answer': problem.answer.content if problem.answer else '',  # 在这里返回标准答案可能需要根据业务决定是否在学生提交前隐藏
            'explanation': problem.answer.explanation if problem.answer else '',
        })
    else:
        data['problem_content'] = assignment.description or "请查看附件完成作业。"

    return JsonResponse({'data': data})


@jwt_login_required
@csrf_exempt
def homeworkGradingProcess(request, assignment_id):
    """
    学生提交作业答案。

    功能描述:
        该视图处理学生提交的作业答案（可以是文本或图片）。
        它会创建一份提交记录（Submission），更新作业状态（AssignmentStatus），
        然后触发一个异步的Celery任务（process_and_grade_submission）来进行自动批改。

    Args:
        request (Request): DRF的Request对象。
            - POST: 包含 'answer_content' (选择题答案) 和/或 'submitted_text' (主观题文本答案)。
            - FILES: 包含 'image' (上传的图片文件)。
        assignment_id (int): 对应的作业状态ID (AssignmentStatus ID)。

    Returns:
        JsonResponse:
            - 成功 (HTTP 200 OK): 返回成功信息，提示正在批改中。
            - 失败 (HTTP 404/500): 返回具体的错误原因。
    """
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)
    try:
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'error': '用户未登录'}, status=401)

        assignment_status = AssignmentStatus.objects.get(id=assignment_id, student=user)

        # 创建提交记录
        # 注意：这里需要根据前端上传的是文本还是图片做不同处理，这里假设前端上传了 answer_content
        # 如果是图片，需要在 request.FILES 中获取

        submission = Submission.objects.create(
            student=user,
            problem=assignment_status.assignment.problem,
            submitted_time=timezone.now(),
            choose_answer=request.POST.get('answer_content'),
            submitted_text=request.POST.get('submitted_text', '')
        )

        # 处理上传的图片
        if 'image' in request.FILES:
            submission.submitted_image = request.FILES['image']
            submission.save()

        assignment_status.submission = submission
        assignment_status.submission.status = 'SUBMITTED'
        assignment_status.submitted_at = timezone.now()
        assignment_status.submission.save()
        assignment_status.save()

        logger.info('正在调用异步批改进程')
        # 调用 Celery 任务
        process_and_grade_submission.delay(assignment_status_id=assignment_status.id)

        return JsonResponse({
            'success': True,
            'message': '作业提交成功，正在批改中',
            'assignment_status_id': assignment_status.id
        })
    except AssignmentStatus.DoesNotExist:
        return JsonResponse({'error': '未查找到对应的作业状态'}, status=404)
    except Exception as e:
        logger.error(f"提交作业失败: {e}")
        return JsonResponse({'error': f'提交失败，请重试，详情：{e}'}, status=500)


@jwt_login_required
def teacher_get_assignments_detail(request, class_id, assignment_id):
    """
    老师获取单个作业的统计详情。

    功能描述:
        该视图供教师（已认证）调用，返回特定班级下单个作业的详细统计信息，
        包括总人数、已提交人数等。

    Args:
        request (Request): DRF的Request对象。
        class_id (int): 目标班级的ID。
        assignment_id (int): 目标作业的ID。

    Returns:
        JsonResponse:
            - 成功 (HTTP 200 OK): 返回包含作业统计信息的JSON对象。
            - 失败 (HTTP 404 NOT FOUND): 如果作业不存在或教师无权访问。
    """
    if request.method == 'GET':
        teacher = request.user
        assignment = Assignment.objects.filter(id=assignment_id, teacher=teacher, target_class__id=class_id).first()
        if not assignment:
            return JsonResponse({'error': '作业不存在'}, status=404)

        submittedCount = 0
        total_members = assignment.target_class.members.count()

        for stu in assignment.target_class.members.all():
            status_obj = AssignmentStatus.objects.filter(student=stu, assignment=assignment).first()
            if status_obj and status_obj.submission and status_obj.submission.status != 'PENDING':
                submittedCount += 1

        return_data = {
            'id': assignment.id,
            'subject': assignment.problem.subject.name if assignment.problem and assignment.problem.subject else '未知',
            'title': assignment.title,
            'description': assignment.description,
            'teacher_name': assignment.teacher.wx_nickName,
            'class_name': assignment.target_class.name,
            'created_at': assignment.created_at.strftime('%Y-%m-%d %H:%M'),
            'deadline': assignment.deadline.strftime('%Y-%m-%d %H:%M') if assignment.deadline else None,
            'totalCount': total_members,
            'submittedCount': submittedCount,
            'problem_id': assignment.problem.id if assignment.problem else None,
            'problem_title': assignment.problem.title if assignment.problem else '传统作业 (仅附件)',
        }
        return JsonResponse({'data': return_data})


@jwt_login_required
def teacher_get_students_assignments_list(request, class_id, assignment_id):
    """
    老师获取某作业下所有学生的提交列表。

    功能描述:
        该视图供教师（已认证）调用，返回指定作业下，班级内所有学生的提交状态和分数列表。
        用于教师查看和管理学生的作业完成情况。

    Args:
        request (Request): DRF的Request对象。
        class_id (int): 目标班级的ID。
        assignment_id (int): 目标作业的ID。

    Returns:
        JsonResponse:
            - 成功 (HTTP 200 OK): 返回一个包含学生提交状态列表的JSON对象。
            - 失败 (HTTP 404 NOT FOUND): 如果作业不存在或教师无权访问。
    """
    if request.method == 'GET':
        teacher = request.user
        assignment = Assignment.objects.filter(id=assignment_id, teacher=teacher, target_class__id=class_id).first()

        if not assignment:
            return JsonResponse({'error': '作业不存在或无权访问'}, status=404)

        student_list = []

        for stu in assignment.target_class.members.all():
            assignment_status = AssignmentStatus.objects.filter(
                student=stu,
                assignment=assignment
            ).first()

            is_submitted = False
            status_text = '未提交'
            score = None

            if assignment_status and assignment_status.submission:
                status_text = assignment_status.submission.status
                score = assignment_status.submission.score
                if status_text != 'PENDING':
                    is_submitted = True

            student_data = {
                'id': stu.id,
                'name': stu.wx_nickName,
                'submitted': is_submitted,
                'status': status_text,
                'score': score
            }
            student_list.append(student_data)

        return JsonResponse({'data': student_list})
    
@api_view(['POST'])
@jwt_login_required
@csrf_exempt
@transaction.atomic
def update_assignment(request, assignment_id):
    """
    编辑/更新作业信息
    """
    try:
        teacher = request.user
        data = request.data
        
        # 1. 获取作业对象，并检查权限
        # 使用 select_related 预加载 problem 和 problem_content，减少数据库查询
        assignment = Assignment.objects.select_related('problem', 'problem__content').get(id=assignment_id)
        
        if assignment.teacher != teacher:
            return Response({'success': False, 'message': '无权修改此作业'}, status=status.HTTP_403_FORBIDDEN)

        # 2. 获取前端提交的数据
        title = data.get('title')
        description = data.get('description')
        deadline = data.get('deadline') # 格式: "2023-11-30 23:59"

        # 3. 更新 Assignment 表
        if title:
            assignment.title = title
        if description:
            assignment.description = description
        if deadline:
            assignment.deadline = deadline
        assignment.save()

        # 4. 同步更新关联的 Problem 表 (如果存在)
        # 因为在 push_assignment 中，我们是用作业的 title 和 description 来填充 Problem 的
        if assignment.problem:
            problem = assignment.problem
            
            # 更新题目标题
            if title:
                problem.title = title
            
            # 更新题目内容 (ProblemContent)
            if description and problem.content:
                problem.content.content = description
                problem.content.save()
            
            problem.save()

        return Response({
            'success': True, 
            'message': '作业修改成功',
            'data': {
                'id': assignment.id,
                'title': assignment.title
            }
        })

    except Assignment.DoesNotExist:
        return Response({'success': False, 'message': '作业不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"更新作业失败: {str(e)}")
        return Response({'success': False, 'message': f'更新失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)