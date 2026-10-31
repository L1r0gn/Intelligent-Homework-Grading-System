"""DKT 模块页面路由。"""
from django.urls import path

from dkt_app import views

app_name = 'dkt_app'

urlpatterns = [
    path('students/', views.student_list_view, name='student_list'),
    path('students/<int:student_id>/mastery/', views.view_student_mastery, name='student_mastery'),
    # 当前登录用户自己的掌握度页面（老师/管理员会被转到学生列表）
    path('my-mastery/', views.my_mastery_view, name='my_mastery'),
]
