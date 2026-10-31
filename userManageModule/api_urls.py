"""用户与班级模块的 JSON 接口（挂在 /api/v1/ 下）。"""
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

import userManageModule.views as user_views
from userManageModule import class_views

app_name = 'user_api'

urlpatterns = [
    # 认证
    path('auth/token/', TokenObtainPairView.as_view(), name='token'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/wechat/', user_views.wx_login, name='wechat_login'),

    # 用户
    path('users/me/', user_views.UserProfileUpdateView.as_view(), name='user_me'),
    path('users/me/avatar/', user_views.wx_upload_avatar, name='user_avatar'),
    path('users/', user_views.user_add, name='user_create'),
    path('users/<int:user_id>/', user_views.wx_user_list, name='user_detail'),
    path('users/<int:user_id>/edit/', user_views.wx_user_edit, name='user_update'),

    # 学生检索
    path('students/search/', class_views.search_students_api, name='student_search'),

    # 班级成员关系
    path('classes/join/', user_views.userAddClass, name='class_join'),
    path('classes/<int:class_id>/members/', user_views.get_class_members, name='class_members'),
    path('classes/<int:class_id>/members/<int:user_id>/', user_views.wx_remove_class_member,
         name='class_member_remove'),
    path('classes/<int:class_id>/leave/', user_views.quit_class, name='class_leave'),
]
