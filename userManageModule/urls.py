from django.urls import path

import userManageModule.views
from userManageModule import views as user_views
urlpatterns = [
# 登录页
path('login/', user_views.login_view, name='login'),
# 注销页
path('logout/', user_views.logout_view, name='logout'),
path('list/', user_views.user_list, name='user_list'),
path('edit/<int:user_id>/', user_views.user_edit, name='user_edit'),
path('delete/<int:user_id>/', user_views.user_delete, name='user_delete'),
path('add/', user_views.user_add, name='user_add'),
path('wx/add/', user_views.user_add, name='wx_user_add'),
path('wx/edit/<int:user_id>', user_views.wx_user_edit, name='wx_user_edit'),
path('wx/list/<int:user_id>/', user_views.wx_user_list, name='wx_user_list'),
path('wx/login',userManageModule.views.wechat_login,name='wx_login'),
]
