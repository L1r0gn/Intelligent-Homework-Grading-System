"""
URL configuration for IntelligentHomeworkGradingSystem project.

命名约定见 docs/URL_SPEC.md：
- 页面路由挂在 /<app>/ 下，页面与接口彻底分离；
- 所有 JSON 接口统一挂在 /api/v1/ 下（见 api/v1/urls.py）；
- 路径参数一律 /<int:xxx>/，结尾必须带斜杠。
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from IntelligentHomeworkGradingSystem import settings
from IntelligentHomeworkGradingSystem import views as core_views
from assignmentAndClassModule.views import student_homework

urlpatterns = [
    path('admin/', admin.site.urls),

    # ---------- 首页 ----------
    path('', core_views.dashboard, name='dashboard'),

    # ---------- 学生端页面 ----------
    path('student/assignments/', student_homework, name='student_assignments'),

    # ---------- API（所有 JSON 接口） ----------
    path('api/v1/', include('api.v1.urls')),

    # ---------- 各业务模块页面 ----------
    path('user/', include('userManageModule.urls', namespace='user')),
    path('question/', include('questionManageModule.urls', namespace='question')),
    path('grading/', include('gradingModule.urls', namespace='grading')),
    path('assignment/', include('assignmentAndClassModule.urls', namespace='assignment')),
    path('bkt/', include('BKTModule.urls', namespace='bkt')),
    path('dkt/', include('dkt_app.urls', namespace='dkt_app')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
