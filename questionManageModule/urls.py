from django.urls import path

from questionManageModule import views as question_views

app_name = 'question'

urlpatterns = [
    # ---------- 题目 ----------
    path('problems/', question_views.question_list, name='problem_list'),
    path('problems/new/', question_views.question_create, name='problem_create'),
    path('problems/import/', question_views.question_batch_import_json, name='problem_import'),
    path('problems/import-template/', question_views.download_import_template, name='problem_import_template'),
    path('problems/import/review/', question_views.question_import_review, name='problem_import_review'),
    path('problems/batch/', question_views.question_batch_action, name='problem_batch'),
    path('problems/<int:question_id>/', question_views.question_detail, name='problem_detail'),
    path('problems/<int:question_id>/edit/', question_views.question_update, name='problem_update'),
    path('problems/<int:question_id>/delete/', question_views.question_delete, name='problem_delete'),

    # ---------- 知识点 ----------
    path('knowledge-points/', question_views.knowledge_point_list, name='kp_list'),
    path('knowledge-points/new/', question_views.knowledge_point_create, name='kp_create'),
    path('knowledge-points/<int:kp_id>/edit/', question_views.knowledge_point_update, name='kp_update'),
    path('knowledge-points/<int:kp_id>/delete/', question_views.knowledge_point_delete, name='kp_delete'),
]
