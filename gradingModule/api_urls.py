"""批改模块的 JSON 接口（挂在 /api/v1/ 下）。"""
from django.urls import path

from gradingModule import views

app_name = 'grading_api'

urlpatterns = [
    # GET 查询我的提交 / POST 提交作答
    path('submissions/', views.submission_collection, name='submission_collection'),
    path('submissions/<int:submission_id>/', views.getASubmission, name='submission_detail'),
    # 图片走视图是因为需要登录态与权限校验，不能放静态目录
    path('submissions/<int:submission_id>/image/', views.serve_submission_image, name='submission_image'),
    # 某次作业下的全部提交
    path('assignments/<int:assignment_id>/submissions/', views.getSubmissionsByAssignmentId,
         name='assignment_submissions'),
]
