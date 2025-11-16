from functools import wraps
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

User = get_user_model()


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