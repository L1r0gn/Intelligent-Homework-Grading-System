from django.urls import path
from dkt_app import views

app_name = 'dkt_app'

urlpatterns = [
    path('mastery/<int:student_id>/', views.get_student_mastery_view, name='get_student_mastery'),
    path('my_mastery/', views.my_mastery_view, name='my_mastery'),
    path('student/<int:student_id>/mastery/', views.view_student_mastery, name='view_student_mastery'),
    path('students/', views.student_list_view, name='student_list'),
]
