"""题库模块的 JSON 接口（挂在 /api/v1/ 下）。"""
from django.urls import path

from assignmentAndClassModule.views import problem_meta_data
from questionManageModule import views as question_views

app_name = 'question_api'

urlpatterns = [
    # 题目读取
    path('questions/meta/', problem_meta_data, name='question_meta'),
    path('questions/random/', question_views.wx_question_detail_random, name='question_random'),
    path('questions/search/', question_views.wx_search_questions, name='question_search'),
    path('questions/<int:question_id>/', question_views.wx_get_question_by_id, name='question_detail'),

    # 学情
    path('students/me/stats/', question_views.wx_get_student_stats, name='student_stats'),

    # 元数据创建（AJAX）
    path('subjects/', question_views.ajax_create_subject, name='subject_create'),
    path('problem-types/', question_views.ajax_create_problem_type, name='problem_type_create'),
]
