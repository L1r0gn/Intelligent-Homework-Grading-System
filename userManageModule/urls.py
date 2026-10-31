from django.urls import path

from userManageModule import class_views
from userManageModule import views as user_views

app_name = 'user'

urlpatterns = [
    # ---------- 认证与个人中心 ----------
    path('login/', user_views.login_view, name='login'),
    path('logout/', user_views.logout_view, name='logout'),
    path('register/', user_views.user_register, name='register'),
    path('profile/', user_views.user_profile, name='profile'),

    # ---------- 用户管理（管理员） ----------
    path('users/', user_views.user_list, name='user_list'),
    path('users/new/', user_views.user_add, name='user_create'),
    path('users/<int:user_id>/edit/', user_views.user_edit, name='user_update'),
    path('users/<int:user_id>/delete/', user_views.user_delete, name='user_delete'),

    # ---------- 教师注册审核 ----------
    path('teachers/pending/', user_views.pending_teachers, name='teacher_pending'),
    path('teachers/<int:user_id>/approve/', user_views.approve_teacher, name='teacher_approve'),
    path('teachers/<int:user_id>/reject/', user_views.reject_teacher, name='teacher_reject'),

    # ---------- 班级管理 ----------
    path('classes/', class_views.class_list_view, name='class_list'),
    path('classes/mine/', class_views.my_class_list_view, name='class_mine'),
    path('classes/new/', class_views.class_create_view, name='class_create'),
    path('classes/join/', class_views.class_join_by_code_view, name='class_join'),
    path('classes/<int:class_id>/', class_views.class_detail_view, name='class_detail'),
    path('classes/<int:class_id>/edit/', class_views.class_edit_view, name='class_update'),
    path('classes/<int:class_id>/delete/', class_views.class_delete_view, name='class_delete'),
    path('classes/<int:class_id>/students/add/', class_views.class_add_student_view, name='class_student_add'),
    path('classes/<int:class_id>/students/<int:student_id>/remove/', class_views.class_remove_student_view,
         name='class_student_remove'),
    path('classes/<int:class_id>/teachers/add/', class_views.class_add_teacher_view, name='class_teacher_add'),
    path('classes/<int:class_id>/teachers/<int:teacher_id>/remove/', class_views.class_remove_teacher_view,
         name='class_teacher_remove'),
]
