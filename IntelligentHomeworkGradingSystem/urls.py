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
from django.contrib import admin
from django.urls import path
from userManageModule import views
from userManageModule.static.plugins.bootstrap import css
urlpatterns = [
    path('admin/', admin.site.urls),
    path('user/list/',views.user_list,name='user_list'),
    path('user/add/',views.user_add,name='user_add'),
    path('class_name/add/',views.class_add),
    path('user/edit/<int:user_id>/', views.user_edit, name='user_edit'),
    path('user/delete/<int:user_id>/', views.user_delete, name='user_delete'),
]
