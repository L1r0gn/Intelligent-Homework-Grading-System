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
urlpatterns = [
    path('admin/', admin.site.urls),
    path('class_name/add/',user_views.class_add,name = 'class_add'),
    path('question/', include('questionManageModule.urls')),  # 添加这一行
    path('user/',include('userManageModule.urls')),
    path('grading/', include('gradingModule.urls')),
    path('',user_views.user_register,name='user_register'),
    path('class/create/', user_views.create_class, name='create_class'),
    path('class/<int:class_id>/',user_views.class_detail,name='class_detail'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
