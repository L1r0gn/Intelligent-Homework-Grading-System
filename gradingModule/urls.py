from django.contrib import admin
from django.urls import path
from gradingModule import views

urlpatterns = [
    path('wx/submit/',views.submissionprocess),
    path('submissions/', views.submission_list, name='submission_list'),
    path('submissions/<int:submission_id>/', views.submission_detail, name='submission_detail'),
    path('submission/<int:submission_id>/regrade/', views.regrade_submission_view, name='regrade_submission'),

]


