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
from userManageModule import views as user_views
from questionManageModule import views as question_views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('user/list/',user_views.user_list,name='user_list'),
    path('user/add/',user_views.user_add,name='user_add'),
    path('class_name/add/',user_views.class_add,name = 'class_add'),
    path('user/edit/<int:user_id>/', user_views.user_edit, name='user_edit'),
    path('user/delete/<int:user_id>/', user_views.user_delete, name='user_delete'),
    path('question/list/', question_views.question_list, name='question_list'),
    path('question/create/', question_views.question_create, name='question_create'),
    path('question/detail/<int:question_id>/', question_views.question_detail, name='question_detail'),
    path('question/update/<int:question_id>/', question_views.question_update, name='question_update'),
    path('question/delete/<int:question_id>/', question_views.question_delete, name='question_delete'),
]
