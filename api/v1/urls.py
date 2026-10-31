"""
API v1 路由聚合入口。

约定（见 docs/URL_SPEC.md）：
- 所有 JSON 接口统一挂在 /api/v1/ 下，页面路由不在此处；
- 路径参数一律 /<int:xxx>/，禁止 key=value；
- 结尾必须带斜杠；
- 路由名用 snake_case，命名空间为 <app>_api。
"""
from django.urls import include, path

urlpatterns = [
    path('', include('userManageModule.api_urls')),
    path('', include('questionManageModule.api_urls')),
    path('', include('gradingModule.api_urls')),
    path('', include('assignmentAndClassModule.api_urls')),
    path('', include('BKTModule.api_urls')),
    path('', include('dkt_app.api_urls')),
]
