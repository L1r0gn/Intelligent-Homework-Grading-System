from functools import wraps
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import redirect
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

# JWT登录验证
def jwt_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 获取Authorization头
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return JsonResponse({
                'code': 401,
                'error': 'Authorization header is required',
                'message': '请提供认证令牌'
            }, status=401)

        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'code': 401,
                'error': 'Invalid authorization format',
                'message': '认证格式错误，应为: Bearer <token>'
            }, status=401)

        # 提取token
        token = auth_header.split(' ')[1]
        if not token:
            return JsonResponse({
                'code': 401,
                'error': 'Token is empty',
                'message': '令牌不能为空'
            }, status=401)

        try:
            # 验证token
            access_token = AccessToken(token)
            user_id = access_token['user_id']

            # 获取用户对象
            request.user = User.objects.get(id=user_id)

        except TokenError as e:
            # Token过期或格式错误
            error_msg = str(e)
            if 'expired' in error_msg.lower():
                return JsonResponse({
                    'code': 40101,  # 自定义代码，表示token过期
                    'error': 'Token has expired',
                    'message': '登录已过期，请重新登录'
                }, status=401)
            else:
                return JsonResponse({
                    'code': 40102,  # 自定义代码，表示token无效
                    'error': 'Token is invalid',
                    'message': '令牌无效'
                }, status=401)

        except User.DoesNotExist:
            return JsonResponse({
                'code': 40103,  # 自定义代码，表示用户不存在
                'error': 'User not found',
                'message': '用户不存在'
            }, status=401)

        except Exception as e:
            # 其他未知错误
            return JsonResponse({
                'code': 500,
                'error': 'Authentication failed',
                'message': '认证失败'
            }, status=500)

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def student_required(view_func):
    """
    Ensure user is authenticated and is a student (user_attribute == 1)
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_attribute != 1:
            messages.error(request, "只有学生可以执行此操作。")
            return redirect('dashboard')  # Redirect to dashboard or appropriate page
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """
    一个装饰器，用于限制只有管理员才能访问特定的视图。

    该装饰器检查当前登录的用户是否经过身份验证，以及其 `user_attribute` 是否
    大于等于3。如果用户未登录，将被重定向到登录页面。如果用户权限不足，
    将显示一条错误消息并重定向到问题列表页面。
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 逻辑1: 检查用户是否已登录
        if not request.user.is_authenticated:
            # 如果未登录，重定向到登录页面
            return redirect('login')
        
        # 逻辑2: 检查用户权限级别
        # 规定 user_attribute >= 3 的用户为管理员
        if request.user.user_attribute < 3:
            logger.info(f'{request.user.username} 没有权限访问该页面')
            messages.error(request, "您没有权限访问该页面。")
            # 权限不足，重定向到非管理员区域，例如问题列表
            return redirect('question_list')
            
        # 逻辑3: 如果权限验证通过，则执行原始视图函数
        return view_func(request, *args, **kwargs)
    return _wrapped_view
