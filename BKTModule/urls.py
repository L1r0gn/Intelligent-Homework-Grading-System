"""BKT 模块页面与后台管理路由（Session 认证）。"""
from django.urls import path

from . import views

app_name = 'bkt'

urlpatterns = [
    # ---------- 看板 ----------
    path('students/dashboard/', views.bkt_student_dashboard, name='student_dashboard'),
    path('classes/dashboard/', views.bkt_class_dashboard, name='class_dashboard'),

    # ---------- 学生知识画像 ----------
    path('students/<int:student_id>/', views.student_knowledge_profile, name='student_profile'),
    path('students/<int:student_id>/prediction/', views.predict_student_performance, name='student_prediction'),

    # ---------- 班级分析 ----------
    path('classes/<str:class_id>/analytics/', views.class_knowledge_analytics, name='class_analytics'),

    # ---------- 模型参数 ----------
    path('knowledge-points/<int:kp_id>/parameters/', views.knowledge_point_parameters, name='kp_parameters'),

    # ---------- 学习事件（网页端，Session 认证） ----------
    path('learning-events/', views.process_learning_event, name='learning_event'),

    # ---------- 数据迁移维护 ----------
    path('maintenance/migrate/', views.migrate_bkt_data, name='migrate'),
]
