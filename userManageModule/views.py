from symtable import Class

import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from IntelligentHomeworkGradingSystem import settings
from django.http import JsonResponse

from .models import class_name,User
from django.contrib import messages  # 解决 messages 未解析
from django.shortcuts import render, redirect, get_object_or_404
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
def user_add(request):
    if request.method == "GET":
        # 获取所有班级信息，用于表单下拉选择（外键关联需要）
        class_list = class_name.objects.all()
        return render(request, "user_add.html", {'class_list': class_list})

    # 处理POST请求
    nickName = request.POST.get('nickName')
    phone = request.POST.get('phone')
    gender = request.POST.get('gender')  # 此时获取的是字符串，需转换为整数
    user_attribute = request.POST.get('userAttribute')  # 对应表单的name="userAttribute"
    class_in_id = request.POST.get('classInfo')  # 对应表单的name="classInfo"

    try:
        # 数据类型转换
        phone = int(phone) if phone else None  # 手机号转为整数
        gender  = int(gender) if gender else None  # 性别转为整数（1/2）
        user_attribute = int(user_attribute) if user_attribute else None  # 属性转为整数（1/2）
        class_in = class_name.objects.get(id=class_in_id) if class_in_id else None  # 外键关联班级

        # 创建用户（字段名与模型完全匹配）
        User.objects.create(
            nickName=nickName,
            phone=phone,
            gender=gender,
            user_attribute=user_attribute,
            class_in=class_in  # 正确关联外键字段class_in
        )
        messages.success(request, '用户添加成功')
        return redirect('/user/list') # 重定向到列表页，避免重复提交

    except Exception as e:
        messages.error(request, f'添加失败: {str(e)}')
        # 回传数据到表单，保留用户输入
        return render(request, 'user_add.html', {
            'nickName': nickName,
            'phone': phone,
            'gender': gender,
            'user_attribute': user_attribute,
            'class_in_id': class_in_id,
            'class_list': class_name.objects.all()  # 回传班级列表
        })
def class_add(request):
    if request.method == "GET":
        return render(request,  "class_add.html")
    name = request.POST.get('name')
    class_name.objects.create(name=name)
    return render(request, 'user_list.html')
#   hxt新增
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, '用户删除成功')
    return redirect('user_list')
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)  # 获取要编辑的用户

    if request.method == "GET":
        # 显示预填充的表单
        class_list = class_name.objects.all()  # 获取所有班级
        return render(request, "user_edit.html", {
            'user': user,  # 当前用户数据
            'class_list': class_list  # 班级列表（用于下拉框）
        })

    # 处理 POST 请求（表单提交）
    nickName = request.POST.get('nickName')
    phone = request.POST.get('phone')
    gender = request.POST.get('gender')
    user_attribute = request.POST.get('userAttribute')
    class_in_id = request.POST.get('classInfo')
    try:
        # 更新用户字段
        user.nickName = nickName
        user.phone = int(phone) if phone else None
        user.gender = int(gender) if gender else None
        user.user_attribute = int(user_attribute) if user_attribute else None
        user.class_in = class_name.objects.get(id=class_in_id) if class_in_id else None
        user.save()  # 保存到数据库

        messages.success(request, '用户信息更新成功')
        return redirect('user_list')  # 重定向到列表页

    except Exception as e:
        messages.error(request, f'更新失败: {str(e)}')
        return render(request, "user_edit.html", {
            'user': user,
            'class_list': class_name.objects.all()
        })


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import User, class_name
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt  # 禁用 CSRF 检查（适用于 API 接口）
def wx_user_edit(request, user_id):
    # 获取指定用户
    user = get_object_or_404(User, id=user_id)

    if request.method == "GET":
        classNameList = class_name.objects.all().values('id', 'name')  # 获取所有班级实例
        response_data = {
            'user': {
                'gender': user.gender,
                'user_attribute': user.user_attribute,
                'class_in': {
                    'id': user.class_in.id if user.class_in else None,
                    'name': user.class_in.name if user.class_in else ''
                },
                'phone': user.phone,
                'nickName': user.nickName,
                'avatarUrl': user.avatarUrl,
                'last_login_time': user.last_login_time
            },
            'classNameList': list(classNameList)
        }
        return JsonResponse(response_data)

    elif request.method == "POST":
        # 获取前端传来的数据
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)

        # 更新用户数据
        if 'gender' in data:
            user.gender = data['gender']
        if 'user_attribute' in data:
            user.user_attribute = data['user_attribute']
        if 'phone' in data:
            user.phone = data['phone']
        if 'class_in' in data:
            class_in_id = data['class_in'].get('id')
            if class_in_id:
                class_in = get_object_or_404(class_name, id=class_in_id)
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