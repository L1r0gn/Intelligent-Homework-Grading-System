"""BKT 模块的 JSON 接口（挂在 /api/v1/ 下，JWT 认证）。"""
from django.urls import path

from . import views

app_name = 'bkt_api'

urlpatterns = [
    path('students/<int:student_id>/knowledge-profile/', views.wx_student_knowledge_profile,
         name='student_knowledge_profile'),
    path('students/<int:student_id>/prediction/', views.wx_predict_student_performance, name='student_prediction'),
    # 单个知识点的掌握状态与学习轨迹
    path('students/<int:student_id>/knowledge-points/<int:kp_id>/state/', views.wx_student_kp_state,
         name='student_kp_state'),
    path('students/<int:student_id>/knowledge-points/<int:kp_id>/traces/', views.wx_student_kp_traces,
         name='student_kp_traces'),
    path('classes/<str:class_id>/analytics/', views.wx_class_knowledge_analytics, name='class_analytics'),
    path('learning-events/', views.wx_process_learning_event, name='learning_event'),
]
