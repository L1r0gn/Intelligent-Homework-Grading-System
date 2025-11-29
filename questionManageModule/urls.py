from django.urls import path
from questionManageModule import views as question_views
# 引入 meta_data 视图，确保前端能获取搜索所需的筛选条件
from assignmentAndClassModule.views import problem_meta_data

urlpatterns = [
    path('list/', question_views.question_list, name='question_list'),
    path('create/', question_views.question_create, name='question_create'),
    path('detail/<int:question_id>/', question_views.question_detail, name='question_detail'),
    path('update/<int:question_id>/', question_views.question_update, name='question_update'),
    path('delete/<int:question_id>/', question_views.question_delete, name='question_delete'),
    path('batch-import-json/', question_views.question_batch_import_json, name='question_batch_import_json'),
    path('questions/batch-action/', question_views.question_batch_action, name='question_batch_action'),
    path('questions/import/review/',question_views.question_import_review, name='question_import_review'),
    path('subjects/ajax_create/', question_views.ajax_create_subject, name='ajax_create_subject'),
    path('problem_types/ajax_create/', question_views.ajax_create_problem_type, name='ajax_create_problem_type'),

    # === 新增：知识点管理路由 ===
    path('knowledge-points/', question_views.knowledge_point_list, name='knowledge_point_list'),
    path('knowledge-points/create/', question_views.knowledge_point_create, name='knowledge_point_create'),
    path('knowledge-points/update/<int:kp_id>/', question_views.knowledge_point_update, name='knowledge_point_update'),
    path('knowledge-points/delete/<int:kp_id>/', question_views.knowledge_point_delete, name='knowledge_point_delete'),

    # 1. 获取题目元数据 (知识点、科目等 - 修复 404)
    # 前端 search.js 依赖此接口获取筛选下拉框的数据
    path('wx/get_problem_meta_data/', problem_meta_data, name='wx_get_problem_meta_data'),
    # 2. 随机获取题目 (原有接口)
    path('wx/detail/random/', question_views.wx_question_detail_random, name='wx_question_detail'),
    # 3. 题目搜索接口 (新增)
    # 前端调用: /question/wx/search/?keyword=...&kp_id=...
    path('wx/search/', question_views.wx_search_questions, name='wx_search_questions'),
    # 4. 获取指定题目详情 (新增)
    # 前端调用: /question/wx/detail/123/
    path('wx/detail/<int:question_id>/', question_views.wx_get_question_by_id, name='wx_get_question_by_id'),
    #用户查看个人情况路由
    path('wx/student/stats/', question_views.wx_get_student_stats, name='wx_get_student_stats'),
]


