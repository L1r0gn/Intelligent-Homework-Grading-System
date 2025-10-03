from django.urls import path
from questionManageModule import views as question_views

urlpatterns = [
    path('list/', question_views.question_list, name='question_list'),
    path('create/', question_views.question_create, name='question_create'),
    path('detail/<int:question_id>/', question_views.question_detail, name='question_detail'),
    path('update/<int:question_id>/', question_views.question_update, name='question_update'),
    path('delete/<int:question_id>/', question_views.question_delete, name='question_delete'),
    path('batch-import-json/', question_views.question_batch_import_json, name='question_batch_import_json'),
    path('wx/detail/random/',question_views.wx_question_detail_random,name='wx_question_detail'),
    path('questions/batch-action/', question_views.question_batch_action, name='question_batch_action'),
    path('questions/import/review/',question_views.question_import_review, name='question_import_review'),
]


