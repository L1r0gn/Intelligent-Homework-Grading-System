# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.db import transaction
from django.utils import timezone
from django.db.models import Count

from gradingModule.models import Submission
from gradingModule.tasks import process_and_grade_submission
from gradingModule.views import logger
from questionManageModule.models import (
    ProblemType, Subject, ProblemTag,
    Problem, ProblemContent, Answer
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
    教师推送作业 (二合一：创建新题目并立即发布)
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
            # (假设答案和解析存在 Answer 表中)
            answer_obj = Answer.objects.create(
                content=answer_text,
                explanation=explanation_text
                # content_data={} # 如果您有结构化答案，也在这里处理
            )

            # 3.2 创建题目内容 (ProblemContent)
            problem_content_obj = ProblemContent.objects.create(
                content=problem_content_text
                # content_data={} # 如果您有结构化内容（如选择题选项），也在这里处理
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
                # got_points, scoringPoint, attachment 暂不处理
            )

            # 3.4 关联 题目标签 (Tags)
            if tag_ids:
                tags = ProblemTag.objects.filter(id__in=tag_ids)
                new_problem.tags.set(tags)

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
                'problem_id': new_problem.id
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
    """学生获取作业列表"""
    student = request.user
    student_classes = student.class_in.all()
    print(f"学生所在班级: {[cls.name for cls in student_classes]}")

    if not student_classes.exists():
        # 注意：这里应该返回 JsonResponse，或者在 Response 中设置 content_type
        return JsonResponse({
            'success': True,
            'data': [],
            'message': '您还没有加入任何班级'
        })

    assignments = Assignment.objects.filter(
        target_class__in=student_classes
    ).select_related('teacher', 'target_class', 'problem').order_by('-created_at')  # 优化查询

    # 收到header查询特定班级
    # logger.info(f'收到header{request.headers}')
    class_id = request.headers.get('ClassId')
    if class_id:
        logger.info(f'查询用户需要查询特定班级的作业，班级id为:{class_id}')
        assignments = assignments.filter(target_class__id=class_id)

    # 一次性获取学生所有作业的状态
    assignments_data = []
    for assignment in assignments:
        assignmentStatusOfThisAssignment = assignment.assignmentstatus_set.filter(assignment=assignment).first()
        if assignmentStatusOfThisAssignment.submission:
            assignment_status = assignmentStatusOfThisAssignment.submission.status
        else:
            assignment_status =  'PENDING'
        assignments_data.append({
            'id': assignment.id,
            'title': assignment.title,
            'description': assignment.description,
            'teacher_name': assignment.teacher.wx_nickName or assignment.teacher.username,
            'class_name': assignment.target_class.name,
            'created_at': assignment.created_at.strftime('%Y-%m-%d %H:%M'),
            'deadline': assignment.deadline.strftime('%Y-%m-%d %H:%M') if assignment.deadline else None,
            # 关联的 Problem 信息
            'problem_id': assignment.problem.id if assignment.problem else None,
            'problem_title': assignment.problem.title if assignment.problem else '传统作业',
            'status': assignment_status,
            'status_text': {
                'PENDING': '待完成',
                'SUBMITTED': '已提交',
                'GRADED': '已批改',
                'WRONG_ANSWER': '答案错误',
                'ACCEPT':'答案正确',
            }.get(assignment_status, '未知'),
            'submitted_at': assignmentStatusOfThisAssignment.submitted_at.strftime('%Y-%m-%d %H:%M') if assignmentStatusOfThisAssignment.submitted_at else None,
        })
    print(f"返回作业数量: {len(assignments_data)}")
    return JsonResponse({
        'success': True,
        'data': assignments_data
    })


@jwt_login_required
def teacher_get_assignments(request, class_id):
    if request.method == 'GET':
        teacher = request.user
        assignments = Assignment.objects.filter(teacher=teacher, target_class__id=class_id)
        return_assignments = []
        for assignment in assignments:
            # 获取该作业的所有学生状态统计
            return_assignments.append({
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'teacher_name': assignment.teacher.wx_nickName,
                'class_name': assignment.target_class.name,
                'created_at': assignment.created_at.strftime('%Y-%m-%d %H:%M'),
                'deadline': assignment.deadline.strftime('%Y-%m-%d %H:%M') if assignment.deadline else None,
                # 关联的 Problem 信息
                'problem_id': assignment.problem.id if assignment.problem else None,
                'problem_title': assignment.problem.title if assignment.problem else '传统作业 (仅附件)',
            })
        return JsonResponse({'data': return_assignments})


@jwt_login_required
def problem_meta_data(request):
    """
    返回题目创建所需的元数据
    """
    try:
        # 获取激活的题目类型
        problem_types = ProblemType.objects.filter(is_active=True).values('id', 'name', 'code')
        # 获取所有科目
        subjects = Subject.objects.all().values('id', 'name', 'code')
        # 获取所有标签
        tags = ProblemTag.objects.all().values('id', 'name', 'color')
        return JsonResponse({
            'success': True,
            'data': {
                'problemTypes': list(problem_types),
                'subjects': list(subjects),
                'tags': list(tags)
            }
        })
    except Exception as e:
        # 这里使用 JsonResponse 与上面保持一致
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@jwt_login_required
def get_student_homework_detail(request, assignment_id):
    """
    学生获取单份作业的详细信息（用于做题页面）
    """
    student = request.user
    # 1. 获取作业对象，同时验证是否存在
    # 使用 select_related 优化后续对关联对象的访问
    try:
        assignment = Assignment.objects.select_related(
            'teacher', 'target_class', 'problem', 'problem__problem_type'
        ).get(id=assignment_id)
    except Assignment.DoesNotExist:
        return JsonResponse({'success': False, 'error': '作业不存在'}, status=404)
    # 2. 验证权限：学生是否在目标班级中
    # 这是一个安全检查，防止学生通过遍历 ID 访问其他班级的作业
    if not student.class_in.filter(id=assignment.target_class.id).exists():
        return JsonResponse({'success': False, 'error': '您不是该班级成员，无法查看此作业'}, status=403)

    # 3. 获取或创建学生的作业状态
    # 如果学生是后加入班级的，可能还没有状态记录，这里使用 get_or_create 自动修复
    status_obj, created = AssignmentStatus.objects.get_or_create(
        assignment=assignment,
        student=student,
        defaults={'status': 'pending'}
    )
    # 4. 准备返回数据
    problem = assignment.problem
    if status_obj.submission:
        status = status_obj.submission.status
        score = status_obj.submission.score
    else:
        status = 'pending'
        score = 0
    # 基础作业信息
    data = {
        'assignment_id': assignment.id,
        'assignment_title': assignment.title,
        'teacher_name': assignment.teacher.wx_nickName or assignment.teacher.username,
        'deadline': assignment.deadline.strftime('%Y-%m-%d %H:%M') if assignment.deadline else None,
        'assignment_status_id': status_obj.id,
        'status': status,
        'score':score,
        'submitted_at': status_obj.submitted_at.strftime('%Y-%m-%d %H:%M') if status_obj.submitted_at else None,
    }

    # 如果有提交记录，获取提交相关信息
    if status_obj.submission:
        data.update({
            'submission_id': status_obj.submission.id,
            # 可以根据需要添加更多提交相关的信息
        })

    # 题目详细信息（如果有）
    if problem:
        # 注意：这里假设 problem.content 是一个关联对象，可能需要进一步查询
        # 如果 problem 模型中 content 就是一个 TextField，则直接使用 problem.content
        # 根据您之前的描述，ProblemContent 是一个单独的模型
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
            # 可以在这里添加更多题目信息，如附件等
        })
    else:
        # 如果是传统作业（没有关联在线题目）
        data['problem_content'] = assignment.description or "请查看附件完成作业。"

    return JsonResponse({'data': data})


@jwt_login_required
@csrf_exempt
def homeworkGradingProcess(request, assignment_id):
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)
    try:
        # 获取当前用户
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'error': '用户未登录'}, status=401)

        # 获取作业状态
        assignment_status = AssignmentStatus.objects.get(id=assignment_id, student=user)

        # 创建提交记录
        from gradingModule.models import Submission
        # logger.info(f'收到了前端发来的数据:{request.POST}')
        submission = Submission.objects.create(
            student=user,
            problem=assignment_status.assignment.problem,
            # 根据实际需要设置其他提交字段
            submitted_time=timezone.now(),
            choose_answer=request.POST.get('answer_content'),
        )
        # logger.info(f'收到了后端发来的answe_content:{request.POST.get("answer_content")}')
        # 更新作业状态
        assignment_status.submission = submission
        assignment_status.submission.status = 'SUBMITTED'
        assignment_status.submitted_at = timezone.now()
        assignment_status.submission.save()
        assignment_status.save()

        # 异步调用批改任务
        logger.info('正在调用异步进程')
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
    if request.method == 'GET':
        teacher = request.user
        assignment = Assignment.objects.filter(id=assignment_id,teacher=teacher, target_class__id=class_id).first()
        # 获取该作业统计
        submittedCount = 0
        for stu in assignment.target_class.members.all():
            if AssignmentStatus.objects.filter(id=stu.id).first().submission:
                if AssignmentStatus.objects.filter(id=stu.id).first().submission.status != 'PENDING':
                    submittedCount+=1
        return_data = {
            'id': assignment.id,
            'subject': assignment.problem.subject.name,
            'title': assignment.title,
            'description': assignment.description,
            'teacher_name': assignment.teacher.wx_nickName,
            'class_name': assignment.target_class.name,
            'created_at': assignment.created_at.strftime('%Y-%m-%d %H:%M'),
            'deadline': assignment.deadline.strftime('%Y-%m-%d %H:%M') if assignment.deadline else None,
            'totalCount': assignment.target_class.members.count(),
            'submittedCount':submittedCount,
            # 关联的 Problem 信息
            'problem_id': assignment.problem.id if assignment.problem else None,
            'problem_title': assignment.problem.title if assignment.problem else '传统作业 (仅附件)',
        }
        return JsonResponse({'data': return_data})

@jwt_login_required
def teacher_get_students_assignments_list(request, class_id, assignment_id):
    if request.method == 'GET':
        teacher = request.user
        assignment = Assignment.objects.filter(id=assignment_id, teacher=teacher, target_class__id=class_id).first()

        if not assignment:
            return JsonResponse({'error': '作业不存在或无权访问'}, status=404)

        # 获取该作业统计
        submittedCount = 0
        student_list = []

        for stu in assignment.target_class.members.all():
            # 修复：应该通过student和assignment来查询AssignmentStatus
            assignment_status = AssignmentStatus.objects.filter(
                student=stu,
                assignment=assignment
            ).first()

            if assignment_status and assignment_status.submission:
                if assignment_status.submission.status != 'PENDING':
                    submittedCount += 1

            # 构建学生数据
            student_data = {
                'id': stu.id,
                'name': stu.wx_nickName,
                # 'studentId': stu.student_id,
                'submitted': assignment_status and assignment_status.submission and assignment_status.submission.status != 'PENDING',
                'status': assignment_status.submission.status if assignment_status and assignment_status.submission else '未提交'
            }
            student_list.append(student_data)
        # 构建返回数据
        return JsonResponse({'data': student_list})