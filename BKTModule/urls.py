# BKTModule URL配置
from django.urls import path
from . import views

app_name = 'bkt'

urlpatterns = [
    # ==================== WEB页面路由 ====================
    path('student/dashboard/', views.bkt_student_dashboard, name='student_dashboard'),
    path('class/dashboard/', views.bkt_class_dashboard, name='class_dashboard'),
    
    # ==================== 微信小程序API路由 (使用JWT认证) ====================
    # 学生知识状态API
    path('wx/student/<int:student_id>/profile/', views.wx_student_knowledge_profile, name='wx_student_profile'),
    path('wx/student/<int:student_id>/prediction/', views.wx_predict_student_performance, name='wx_student_prediction'),
    
    # 班级分析API
    path('wx/class/<str:class_id>/analytics/', views.wx_class_knowledge_analytics, name='wx_class_analytics'),
    
    # 学习事件处理API
    path('wx/process-learning-event/', views.wx_process_learning_event, name='wx_process_learning_event'),
    
    # ==================== 本地管理系统API路由 (使用Session认证) ====================
    # 学生知识状态API
    path('student/<int:student_id>/profile/', views.student_knowledge_profile, name='student_profile'),
    path('student/<int:student_id>/prediction/', views.predict_student_performance, name='student_prediction'),
    
    # 班级分析API
    path('class/<str:class_id>/analytics/', views.class_knowledge_analytics, name='class_analytics'),
    
    # BKT模型管理API
    path('knowledge-point/<int:kp_id>/parameters/', views.knowledge_point_parameters, name='kp_parameters'),
    
    # 学习事件处理API
    path('process-learning-event/', views.process_learning_event, name='process_learning_event'),
    
    # 数据迁移API
    path('migrate-data/', views.migrate_bkt_data, name='migrate_data'),
]