from audioop import reverse
from functools import wraps

import requests
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from IntelligentHomeworkGradingSystem import settings
from django.http import JsonResponse

from .forms import UserAddForm
from .models import className,User
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
#登录验证
def admin_required(view_func):
    """自定义装饰器：仅允许管理员（user_attribute >= 3）访问"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        if request.user.user_attribute < 3:
            print(request.user.username,'没有权限访问该页面')
            messages.error(request, "您没有权限访问该页面。")
            return redirect('login')  # 或重定向到首页
        return view_func(request, *args, **kwargs)
    return _wrapped_view
def login_view(request):
    """
    处理用户登录请求
    """
    if request.user.is_authenticated:
        return redirect('user_list')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        print(username, password)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # 1. 使用 Django 的标准方式安全地验证用户名和密码
            # 它会自动处理密码哈希的比较，非常安全
            if not username:
                print('username error')
            user = authenticate(request, username=username, password=password)
            # 2. 检查用户是否存在
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'user_list')
                return redirect(next_url)
            else:
                # 用户名或密码错误，显示通用错误信息
                messages.error(request, "用户名或密码错误，请重试。")
        else:
            # 表单本身无效（例如字段为空），也显示错误信息
            messages.error(request, "用户名或密码无效。")
            print(form.errors)
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})
# 建议同时添加一个注销视图
def logout_view(request):
    """
    处理用户注销请求
    """
    logout(request)
    # 注销后重定向到登录页面
    return redirect('login')
@admin_required
def user_list(request):
    queryset = User.objects.all()
    return render(request, "user_list.html", {'queryset': queryset})
def wx_user_list(request, user_id):
    try:
        # 用 get 直接获取单个用户，更符合“查询单个用户”场景
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': '用户不存在'}, status=404)

        # 处理关联字段和枚举值转换（关键优化）
    class_name = user.class_in.name if user.class_in else None  # 处理班级为空的情况
    # 性别转换：1→男，2→女，其他→None
    gender_map = {1: '男', 2: '女'}
    gender = gender_map.get(user.gender)

    # 用户属性转换：1→student，2→teacher
    attribute_map = {1: 'student', 2: 'teacher'}
    user_attribute = attribute_map.get(user.user_attribute)

    # 构造响应数据（包含前端需要的所有字段）
    data = {
        'id': user.id,
        'wx_nickName': user.wx_nickName,
        'wx_avatar': user.wx_avatar,
        'phone': user.phone,
        'gender': gender,  # 返回转换后的文本（男/女/None）
        'user_attribute': user_attribute,  # 返回转换后的文本（student/teacher/None）
        'class_in': {
            'name': class_name  # 班级名称（空则为None）
        },
        'wx_country': user.wx_country,
        'wx_province': user.wx_province,
        'wx_city': user.wx_city,
        'last_login_time': user.last_login_time.strftime('%Y-%m-%d %H:%M:%S')  # 格式化时间
    }
    print(data)
    return JsonResponse({'data': data}, status=200)  # 直接返回单个对象
@admin_required
def user_add(request):
    if request.method == 'POST':
        # 如果是POST请求，用提交的数据实例化表单
        form = UserAddForm(request.POST)
        if form.is_valid(): # is_valid() 会自动运行所有验证逻辑
            form.save() # 调用我们重写的save方法，安全地创建用户
            messages.success(request, '用户添加成功！')
            return redirect('/user/list/') # 建议使用URL名称: redirect('user_list')
    else:
        # 如果是GET请求，创建一个空的表单
        form = UserAddForm()

    # 无论是GET请求还是表单验证失败，都渲染同一个页面
    # 如果验证失败，form对象会包含错误信息，并自动在模板中显示
    return render(request, "user_add.html", {'form': form})
@admin_required
def class_add(request):
    if request.method == "GET":
        return render(request,  "class_add.html")
    name = request.POST.get('name')
    className.objects.create(name=name)
    return render(request, 'user_list.html')
@admin_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, '用户删除成功')
    return redirect('user_list')
@admin_required
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)  # 获取要编辑的用户
    print('正在编辑',user.username,'的数据')
    if request.method == "GET":
        # 显示预填充的表单
        class_list = className.objects.all()  # 获取所有班级
        return render(request, "user_edit.html", {
            'user': user,  # 当前用户数据
            'class_list': class_list  # 班级列表（用于下拉框）
        })

    # 处理 POST 请求（表单提交）
    if request.method == "POST":
        nickname = request.POST.get('nickName')
        password = request.POST.get('password')
        username = request.POST.get('username')
        phone = request.POST.get('phone')
        gender = request.POST.get('gender')
        user_attribute = request.POST.get('userAttribute')
        print(user_attribute)
        class_in_id = request.POST.get('classInfo')
        try:
            # 更新用户字段
            user.nickName = nickname
            user.phone = int(phone) if phone!=None else 13500000000
            user.gender = int(gender) if gender else None
            user.username = username
            user.password = password
            user.user_attribute = user_attribute if user_attribute else 0
            if user_attribute == 4 and request.user.user_attribute != 4:
                print(user,"只有超级管理员可以设置超级管理员权限。")
                messages.error(request, "只有超级管理员可以设置超级管理员权限。")
                return redirect('user_list')
            user.is_staff = user_attribute in (3, 4)
            user.class_in = className.objects.get(id=class_in_id) if class_in_id else None
            user.save()  # 保存到数据库
            print(user,'用户信息更新成功')
            messages.success(request, '用户信息更新成功')
            return redirect('user_list')  # 重定向到列表页
        except ValueError as e:
            # 特别处理 int() 转换错误
            print(request, f"输入数据格式错误：{str(e)}")
            return render(request, "user_edit.html", {
                'user': user,
                'class_list': className.objects.all()
            })
        except className.DoesNotExist:
            print(request, "班级不存在")
            return render(request, "user_edit.html", {
                'user': user,
                'class_list': className.objects.all()
            })
        except Exception as e:
            # 记录日志（生产环境用 logging）
            print(f"更新用户 {user.id} 失败: {e}")
            print(request, f"更新失败：{str(e)}")
            return render(request, "user_edit.html", {
                'user': user,
                'class_list': className.objects.all()
            })
@csrf_exempt  # 禁用 CSRF 检查（适用于 API 接口）
def wx_user_edit(request, user_id):
    # 获取指定用户
    user = get_object_or_404(User, id=user_id)

    #前端传过来 ： POST / GET -> 提交至后端 / 从后端获取
    if request.method == "GET":
        classNameList = className.objects.all().values('id', 'name')  # 获取所有班级实例
        response_data = {
            'user': {
                'gender': user.gender,
                'user_attribute': user.user_attribute,
                'class_in': {
                    'id': user.class_in.id if user.class_in else None,
                    'name': user.class_in.name if user.class_in else ''
                },
                'phone': user.phone,
                'last_login_time': user.last_login_time
            },
            'classNameList': list(classNameList)
        }
        return JsonResponse(response_data)

    elif request.method == "POST":
        # 获取前端传来的数据
        try:
            import json
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)

        # 更新用户数据
        if 'gender' in data:
            user.gender = data['gender']
        if 'attribute' in data:
            user.user_attribute = data['attribute']
        if 'phone' in data:
            user.phone = data['phone']
        if 'class_in' in data:
            class_in_id = data['class_in'].get('id')
            if class_in_id:
                class_in = get_object_or_404(className, id=class_in_id)
                user.class_in = class_in
            else:
                user.class_in = None
        user.save()
        response_data = {
            'user': {
                'gender': user.gender,
                'user_attribute': user.user_attribute,
                'class_in': {
                    'id': user.class_in.id if user.class_in else None,
                    'name': user.class_in.name if user.class_in else ''
                },
                'phone': user.phone,
                'last_login_time': user.last_login_time
            }
        }
        return JsonResponse(response_data)
@api_view(['POST'])
@permission_classes([AllowAny])
def wechat_login(request):
    """微信小程序登录接口 - 函数视图实现"""
    code = request.data.get('code')  # 从前端获取code
    nickName = request.data.get('nickName')  # 从前端获取nickName
    avatarUrl = request.data.get('avatarUrl')  # 从前端获取avatarUrl
    if not code:
        print("登录请求缺少code参数")  # 记录警告日志
        return Response({'error': '缺少code参数'}, status=status.HTTP_400_BAD_REQUEST)

    # 读取微信配置（提前检查配置是否存在）
    appid = getattr(settings, 'WECHAT_APPID', None)
    secret = getattr(settings, 'WECHAT_SECRET', None)
    if not appid or not secret:
        print("微信登录配置缺失：WECHAT_APPID或WECHAT_SECRET未设置")
        return Response({'error': '服务器配置错误'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 微信code2Session接口URL
    url = f'https://api.weixin.qq.com/sns/jscode2session?appid={appid}&secret={secret}&js_code={code}&grant_type=authorization_code'

    try:
        # 调用微信接口，设置超时时间（避免请求挂起）
        response = requests.get(url, timeout=10)  # 超时时间10秒
        response.raise_for_status()  # 触发HTTP错误（如404、500）
        response_data = response.json()

        # 处理微信接口返回的错误
        if 'errcode' in response_data and response_data['errcode'] != 0:
            err_msg = response_data.get('errmsg', '未知错误')
            print(f"微信code2Session失败：errcode={response_data['errcode']}, errmsg={err_msg}")
            return Response({
                'error': '微信登录失败',
                'detail': err_msg,
                'errcode': response_data['errcode']  # 返回微信错误码，便于调试
            }, status=status.HTTP_400_BAD_REQUEST)

        # 提取关键信息
        openid = response_data.get('openid')
        session_key = response_data.get('session_key')
        if not openid or not session_key:
            print(f"微信接口未返回openid或session_key：{response_data}")
            return Response({'error': '获取用户身份失败'}, status=status.HTTP_400_BAD_REQUEST)

        # 数据库操作（单独捕获数据库异常）
        try:
            user, created = User.objects.get_or_create(openid=openid)
            user.session_key = session_key  # 确保User模型有session_key字段
            user.wx_nickName = nickName
            user.wx_avatar = avatarUrl
            user.save(update_fields=['session_key','wx_nickName','wx_avatar'])  # 只更新需要的字段，提高性能
        except Exception as e:
            print(f"用户创建/更新失败：{str(e)}")  # 记录堆栈信息
            return Response({'error': '用户信息存储失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 生成JWT（单独捕获JWT相关异常）
        try:
            refresh = RefreshToken.for_user(user)
        except Exception as e:
            print(f"JWT令牌生成失败：{str(e)}")
            return Response({'error': '认证令牌生成失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 登录成功，记录日志
        print(f"用户登录成功：openid={openid}, 用户ID={user.id}, 新用户={created}")
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': user.id,
            'is_new_user': created,
            'code':200
        }, status=status.HTTP_200_OK)

    # 细分异常类型
    except requests.exceptions.Timeout:
        print("调用微信接口超时")
        return Response({'error': '微信接口响应超时'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except requests.exceptions.RequestException as e:  # 网络错误（如连接失败、HTTP 500）
        print(f"微信接口网络请求失败：{str(e)}")
        return Response({'error': '微信接口请求失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:  # 其他未捕获异常
        print(f"登录接口未知错误：{str(e)}")
        return Response({'error': '服务器内部错误'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
