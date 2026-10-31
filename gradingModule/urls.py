from django.urls import path

from gradingModule import views

app_name = 'grading'

urlpatterns = [
    path('submissions/', views.submission_list, name='submission_list'),
    path('submissions/batch/', views.submission_batch_action, name='submission_batch'),
    path('submissions/<int:submission_id>/', views.submission_detail, name='submission_detail'),
    path('submissions/<int:submission_id>/regrade/', views.regrade_submission_view, name='submission_regrade'),
]
