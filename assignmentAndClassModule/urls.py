from django.urls import path

from assignmentAndClassModule import views

app_name = 'assignment'

urlpatterns = [
    path('assignments/', views.assignment_list_web, name='list'),
    path('assignments/<int:assignment_id>/', views.assignment_detail_web, name='detail'),
]
