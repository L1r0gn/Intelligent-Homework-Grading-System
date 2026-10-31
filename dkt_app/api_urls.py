"""DKT 模块的 JSON 接口（挂在 /api/v1/ 下）。"""
from django.urls import path

from dkt_app import views

app_name = 'dkt_api'

urlpatterns = [
    path('students/<int:student_id>/mastery/', views.get_student_mastery_view, name='student_mastery'),
]
