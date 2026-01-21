from django.urls import path

import userManageModule.views
from userManageModule import views as user_views
urlpatterns = [
    # 网页端 - 用户登录
    path('login/', user_views.login_view, name='login'),
    # 网页端 - 用户注销
    path('logout/', user_views.logout_view, name='logout'),
    # 网页端 - 用户列表（管理员）
    path('list/', user_views.user_list, name='user_list'),
    # 网页端 - 编辑用户信息
    path('edit/<int:user_id>/', user_views.user_edit, name='user_edit'),
    # 网页端 - 删除用户
    path('delete/<int:user_id>/', user_views.user_delete, name='user_delete'),
    # 网页端 - 添加用户
    path('add/', user_views.user_add, name='user_add'),
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
