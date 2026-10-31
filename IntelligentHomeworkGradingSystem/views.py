from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import logging

from userManageModule.models import User, className
from questionManageModule.models import Problem
from gradingModule.models import Submission
from assignmentAndClassModule.models import Assignment, AssignmentStatus

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="app.log"
)
logger = logging.getLogger(__name__)


def helloWorld(request):
    return HttpResponse("Hello World!")


# 批改状态 -> 视觉色系（与页面 Badge 保持一致）
STATUS_TONE = {
    'PENDING': 'warning',
    'GRADING': 'info',
    'SUBMITTED': 'secondary',
    'GRADED': 'primary',
    'ACCEPTED': 'success',
    'WRONG_ANSWER': 'danger',
    'COMPILE_ERROR': 'danger',
    'RUNTIME_ERROR': 'danger',
}


def _dashboard_scope(user):
    """
    按角色给仪表盘划定数据范围。

    管理员（user_attribute >= 3）看全站；
    教师及其他角色只看自己带的班级、以及自己在题库中创建的题目。
    返回 (提交, 学生, 题目, 班级, 作业, 是否全站)。
    """
    if user.user_attribute >= 3:
        return (
            Submission.objects.all(),
            User.objects.filter(user_attribute=1),
            Problem.objects.all(),
            className.objects.all(),
            Assignment.objects.all(),
            True,
        )

    my_classes = className.objects.filter(
        Q(homeroom_teacher=user) | Q(created_by=user) | Q(teachers__teacher=user)
    ).distinct()
    my_students = User.objects.filter(user_attribute=1, class_in__in=my_classes).distinct()
    my_submissions = Submission.objects.filter(
        Q(student__in=my_students) | Q(problem__creator=user)
    )
    my_problems = Problem.objects.filter(creator=user)
    my_assignments = Assignment.objects.filter(
        Q(teacher=user) | Q(target_class__in=my_classes)
    ).distinct()
    return my_submissions, my_students, my_problems, my_classes, my_assignments, False


def _weak_knowledge_points(limit=5):
    """BKT 掌握度最低的知识点；BKT 表缺失或无数据时安静降级。"""
    from BKTModule.models import BKTStudentState

    try:
        rows = (
            BKTStudentState.objects
            .values('knowledge_point__name')
            .annotate(mastery=Avg('mastery_probability'), samples=Count('id'))
            .order_by('mastery')[:limit]
        )
        return [
            {
                'name': row['knowledge_point__name'] or '未命名知识点',
                'percent': round((row['mastery'] or 0) * 100, 1),
                'samples': row['samples'],
            }
            for row in rows
        ]
    except Exception as exc:  # 表不存在 / 版本差异都不该让首页挂掉
        logger.warning("读取 BKT 掌握度失败，已跳过薄弱知识点卡片：%s", exc)
        return []


def _relative_time(moment, now):
    """中文相对时间，避免依赖 Django 的英文 timesince 文案。"""
    seconds = int((now - moment).total_seconds())
    if seconds < 60:
        return '刚刚'
    if seconds < 3600:
        return f'{seconds // 60} 分钟前'
    if seconds < 86400:
        return f'{seconds // 3600} 小时前'
    if seconds < 86400 * 30:
        return f'{seconds // 86400} 天前'
    return timezone.localtime(moment).strftime('%Y-%m-%d')


@login_required(login_url='user:login')
def dashboard(request):
    """
    系统首页仪表盘（工作台）

    面向教师与管理员，回答三个问题：现在要处理什么、最近趋势如何、哪里最需要补。
    """
    user = request.user

    # 学生直接重定向到学生端
    if user.user_attribute == 1:
        return redirect('student_assignments')

    now = timezone.now()
    today = timezone.localdate()
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)

    submissions, students, problems, classes, assignments, is_admin = _dashboard_scope(user)

    # ---------- 待办 ----------
    pending_qs = submissions.filter(status__in=['PENDING', 'GRADING'])
    pending_count = pending_qs.count()
    # 超过 24 小时仍未批改，单独提示，避免"积压"被总数掩盖
    overdue_count = pending_qs.filter(submitted_time__lt=now - timedelta(hours=24)).count()

    pending_teacher_count = 0
    if is_admin:
        pending_teacher_count = User.objects.filter(
            user_attribute=2, is_active=False
        ).count()

    due_soon = list(
        assignments.filter(
            deadline__gte=now, deadline__lte=now + timedelta(days=3)
        ).order_by('deadline')[:4]
    )

    unsubmitted_count = AssignmentStatus.objects.filter(
        assignment__in=assignments, submission__isnull=True
    ).count()

    todos = []
    if pending_count:
        todos.append({
            'icon': 'fa-hourglass-half', 'tone': 'warning',
            'label': '待批改提交', 'count': pending_count,
            'hint': f'其中 {overdue_count} 份超过 24 小时' if overdue_count else '',
            'url': 'grading:submission_list',
            # 直接落到"待批改"筛选结果，少点一次
            'query': '?status=PENDING',
        })
    if pending_teacher_count:
        todos.append({
            'icon': 'fa-user-clock', 'tone': 'info',
            'label': '待审核教师', 'count': pending_teacher_count,
            'hint': '审核通过后教师才能登录', 'url': 'user:teacher_pending',
            'query': '',
        })
    if unsubmitted_count:
        todos.append({
            'icon': 'fa-file-circle-exclamation', 'tone': 'danger',
            'label': '未提交作业记录', 'count': unsubmitted_count,
            'hint': '已过截止时间的建议尽快处理', 'url': 'assignment:list',
            'query': '',
        })

    # ---------- 指标 ----------
    week_count = submissions.filter(submitted_time__gte=week_start).count()
    prev_week_count = submissions.filter(
        submitted_time__gte=prev_week_start, submitted_time__lt=week_start
    ).count()
    if prev_week_count:
        week_delta = round((week_count - prev_week_count) / prev_week_count * 100)
        week_delta_dir = 'up' if week_delta >= 0 else 'down'
        week_delta_text = f'{abs(week_delta)}%'
    else:
        week_delta_dir = None
        week_delta_text = None

    # 得分率 = Σ得分 / Σ题目总分，比裸平均分更经得起"题目分值不一致"的考验
    rate_agg = submissions.filter(
        score__isnull=False, problem__points__gt=0
    ).aggregate(gain=Sum('score'), possible=Sum('problem__points'))
    possible = rate_agg['possible'] or 0
    score_rate = round((rate_agg['gain'] or 0) / possible * 100, 1) if possible else None

    active_students = (
        submissions.filter(submitted_time__gte=week_start)
        .values('student_id').distinct().count()
    )

    kpi = {
        'pending': pending_count,
        'overdue': overdue_count,
        'week_count': week_count,
        'week_delta_dir': week_delta_dir,
        'week_delta_text': week_delta_text,
        'score_rate_text': f'{score_rate}%' if score_rate is not None else '—',
        'active_students': active_students,
        'student_total': students.count(),
        'question_total': problems.count(),
        'submission_total': submissions.count(),
        'class_total': classes.count(),
    }

    # ---------- 近 14 天趋势 ----------
    trend_start = today - timedelta(days=13)
    trend_rows = (
        submissions.filter(submitted_time__gte=now - timedelta(days=14))
        .annotate(day=TruncDate('submitted_time'))
        .values('day')
        .annotate(
            total=Count('id'),
            gain=Sum('score'),
            possible=Sum('problem__points', filter=Q(score__isnull=False)),
        )
        .order_by('day')
    )
    by_day = {row['day']: row for row in trend_rows}

    trend = {'labels': [], 'counts': [], 'rates': []}
    for offset in range(14):
        day = trend_start + timedelta(days=offset)
        row = by_day.get(day)
        trend['labels'].append(day.strftime('%m-%d'))
        trend['counts'].append(row['total'] if row else 0)
        day_possible = (row['possible'] or 0) if row else 0
        if row and day_possible:
            trend['rates'].append(round((row['gain'] or 0) / day_possible * 100, 1))
        else:
            trend['rates'].append(0)

    # ---------- 批改状态分布 ----------
    label_map = dict(Submission.STATUS_CHOICES)
    status_rows = submissions.values('status').annotate(total=Count('id')).order_by('-total')
    status_dist = [
        {
            'label': label_map.get(row['status'], row['status']),
            'count': row['total'],
            'tone': STATUS_TONE.get(row['status'], 'secondary'),
        }
        for row in status_rows
    ]

    recent = (
        submissions.select_related('student', 'problem')
        .order_by('-submitted_time')[:6]
    )

    context = {
        'is_admin': is_admin,
        'scope_label': '全站数据' if is_admin else '我的班级数据',
        'kpi': kpi,
        'todos': todos,
        'due_soon': due_soon,
        'unsubmitted_count': unsubmitted_count,
        'trend': trend,
        'status_dist': status_dist,
        'weak_kps': _weak_knowledge_points(),
        'recent_submissions': [
            {'obj': item, 'rel_time': _relative_time(item.submitted_time, now)}
            for item in recent
        ],
    }
    return render(request, 'dashboard.html', context)

