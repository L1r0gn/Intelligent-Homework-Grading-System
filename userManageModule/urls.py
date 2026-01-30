from django.urls import path

import userManageModule.views
from userManageModule import views as user_views
from userManageModule import class_views

urlpatterns = [
    # 网页端 - 用户登录
    path('login/', user_views.login_view, name='login'),
    # 网页端 - 用户注销
    path('logout/', user_views.logout_view, name='logout'),
    # 网页端 - 个人中心
    path('profile/', user_views.user_profile, name='user_profile'),
    # 网页端 - 用户列表（管理员）
    path('list/', user_views.user_list, name='user_list'),
    # 网页端 - 编辑用户信息
    path('edit/<int:user_id>/', user_views.user_edit, name='user_edit'),
    # 网页端 - 删除用户
    path('delete/<int:user_id>/', user_views.user_delete, name='user_delete'),
    # 网页端 - 添加用户
    path('add/', user_views.user_add, name='user_add'),

    # REST API - 用户个人信息更新
    path('api/profile/update/', user_views.UserProfileUpdateView.as_view(), name='api_user_profile_update'),

    # 网页端 - 班级管理
    path('class/list/', class_views.class_list_view, name='class_list_web'),
    path('class/my/', class_views.my_class_list_view, name='my_class_list_web'),  # 新增：我的班级管理
    path('class/create/', class_views.class_create_view, name='class_create_web'),
    path('class/edit/<int:class_id>/', class_views.class_edit_view, name='class_edit_web'),
    path('class/delete/<int:class_id>/', class_views.class_delete_view, name='class_delete_web'),
    path('class/detail/<int:class_id>/', class_views.class_detail_view, name='class_detail_web'),
    path('class/student/add/<int:class_id>/', class_views.class_add_student_view, name='class_add_student_web'),
    path('class/student/remove/<int:class_id>/<int:student_id>/', class_views.class_remove_student_view, name='class_remove_student_web'),
    path('class/teacher/add/<int:class_id>/', class_views.class_add_teacher_view, name='class_add_teacher_web'),
    path('class/teacher/remove/<int:class_id>/<int:teacher_id>/', class_views.class_remove_teacher_view, name='class_remove_teacher_web'),
    path('api/student/search/', class_views.search_students_api, name='search_students_api'),

    # 微信小程序端 - 添加用户 (复用了网页端视图)
    path('wx/add/', user_views.user_add, name='wx_user_add'),
    # 微信小程序端 - 编辑用户信息
    path('wx/edit/<int:user_id>', user_views.wx_user_edit, name='wx_user_edit'),
    # 微信小程序端 - 获取用户详情
    path('wx/list/<int:user_id>/', user_views.wx_user_list, name='wx_user_list'),
    # 微信小程序端 - 登录
    path('wx/login/',userManageModule.views.wx_login,name='wx_login'),
    # 微信小程序端 - 用户注册 (当前已禁用)
    # path('register',userManageModule.views.user_register,name='user_register'),
    # 微信小程序端 - 学生加入班级
    path('wx/userJoinClass/',userManageModule.views.userAddClass,name='wx_userJoinClass'),
]