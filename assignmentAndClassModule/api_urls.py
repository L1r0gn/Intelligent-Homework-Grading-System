"""作业模块的 JSON 接口（挂在 /api/v1/ 下）。"""
from django.urls import path

from assignmentAndClassModule import views

app_name = 'assignment_api'

urlpatterns = [
    # 教师端：布置作业
    path('assignments/', views.push_assignment, name='assignment_create'),
    path('assignments/batch/', views.batch_push_assignments, name='assignment_batch'),
    path('assignments/<int:assignment_id>/', views.get_student_homework_detail, name='assignment_detail'),
    path('assignments/<int:assignment_id>/update/', views.update_assignment, name='assignment_update'),

    # 学生端：我的作业
    path('students/me/assignments/', views.student_assignments, name='student_assignments'),

    # 教师端：按班级查看
    path('classes/<int:class_id>/assignments/', views.teacher_get_assignments, name='class_assignments'),
    path('classes/<int:class_id>/assignments/<int:assignment_id>/', views.teacher_get_assignments_detail,
         name='class_assignment_detail'),
    path('classes/<int:class_id>/assignments/<int:assignment_id>/students/',
         views.teacher_get_students_assignments_list, name='class_assignment_students'),
]
