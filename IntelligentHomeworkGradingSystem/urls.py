"""
URL configuration for IntelligentHomeworkGradingSystem project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path,include

from IntelligentHomeworkGradingSystem import settings
from userManageModule import views as user_views
from IntelligentHomeworkGradingSystem import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('class_name/add/',user_views.class_add,name = 'class_add'), # 处理添加新班级的请求（网页端）。
    path('question/', include('questionManageModule.urls')),
    path('user/',include('userManageModule.urls')),
    path('grading/', include('gradingModule.urls')),
    path('assignment/', include('assignmentAndClassModule.urls')),
    path('bkt/', include('BKTModule.urls')),  # BKT模块路由
    path('dkt/', include('dkt_app.urls')), # DKT模块路由
    path('', core_views.dashboard, name='dashboard'), # DASHBOARD
    path('register/',user_views.user_register,name='user_register'), # Moved register to /register/
    path('class/create/', user_views.create_class, name='create_class'),
    path('class/<int:class_id>/',user_views.class_detail,name='class_detail'),
    path('class/<int:class_id>/members/', user_views.get_class_members, name='get_class_members'),
    path('class/class_id=<int:class_id>/quit/', user_views.quit_class, name='quit_class'), # 处理学生退出班级的 API 请求

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
