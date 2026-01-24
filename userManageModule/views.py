from functools import wraps
from django.contrib.auth.decorators import login_required
import requests
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken
from IntelligentHomeworkGradingSystem import settings
from .decorators import jwt_login_required
from .forms import UserAddForm
from .models import User, className
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
import logging
import string
import random
from userManageModule.serializers import serializeUserInfo
import json
from django.http import JsonResponse
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import UserProfileUpdateSerializer

logger = logging.getLogger(__name__)

@login_required(login_url='login')
def user_profile(request):
    """
    用户个人中心视图
    允许用户查看和编辑自己的基本信息
    """
    user = request.user
    if request.method == 'POST':
        nick_name = request.POST.get('nickName')
        phone = request.POST.get('phone')
        
        # 简单验证和更新
        if nick_name:
            user.wx_nickName = nick_name
        
        if phone:
            try:
                user.phone = int(phone)
            except ValueError:
                messages.error(request, '电话号码格式不正确')
                return render(request, 'user_profile.html', {'user': user})
                
        user.save()
        messages.success(request, '个人信息更新成功')
        return redirect('user_profile')
    
    return render(request, 'user_profile.html', {'user': user})

#登录验证
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

@csrf_exempt
def wx_login(request):
    """
    处理微信小程序登录请求
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # 从 request.body 中获取原始 JSON 数据并解析
        json_data = json.loads(request.body)
        code = json_data.get('code')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON or missing request body'}, status=400)

    if not code:
        return JsonResponse({'error': 'Missing code'}, status=400)

    # 调用微信接口换取 openid
    appid = settings.WECHAT_APPID
    secret = settings.WECHAT_SECRET
    url = f"https://api.weixin.qq.com/sns/jscode2session?appid={appid}&secret={secret}&js_code={code}&grant_type=authorization_code"

    try:
        resp = requests.get(url)
        data = resp.json()
        openid = data.get('openid')

        if not openid:
            logger.error(f"WeChat login failed: {data}")
            return JsonResponse({'error': f"WeChat login failed: {data.get('errmsg', '')}"}, status=401)

        # 根据 openid 查找或创建用户
        user, created = User.objects.get_or_create(
            openid=openid,
            defaults={'username': openid}  # 首次创建时，可以用 openid 作为默认用户名
        )
        
        # 修复可能存在的用户名为空的情况
        if not user.username:
            user.username = openid
            user.save()

        # 为用户生成 JWT Token
        refresh = RefreshToken.for_user(user)
        # 返回 access 和 refresh token，与前端期望一致
        return JsonResponse({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': user.id,
        })
    except Exception as e:
        logger.error(f"wx_login internal error: {e}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)

def login_view(request):
    """
    处理网页端用户的登录请求。
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            if not username:
                logger.info('username error')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'user_list')
                return redirect(next_url)
            else:
                messages.error(request, "用户名或密码错误，请重试。")
        else:
            messages.error(request, "用户名或密码无效。")
            logger.info(form.errors)
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})

def logout_view(request):
    """
    处理用户的注销请求。
    """
    logout(request)
    return redirect('login')

@admin_required
def user_list(request):
    """
    显示所有用户的列表页面。
    """
    queryset = User.objects.all()
    return render(request, "user_list.html", {'queryset': queryset})

@jwt_login_required
def wx_user_list(request, user_id):
    """
    为微信小程序端提供指定用户的详细信息。
    """
    data = serializeUserInfo(user_id)
    logger.info('发送用户数据：%s',data)
    return JsonResponse({'data': data}, status=200)

@admin_required
def user_add(request):
    """
    处理管理员在网页端添加新用户的请求。
    """
    if request.method == 'POST':
        form = UserAddForm(request.POST)
        if form.is_valid(): 
            form.save() 
            messages.success(request, '用户添加成功！')
            return redirect('/user/list/')
    else:
        form = UserAddForm()

    return render(request, "user_add.html", {'form': form})

@admin_required
def class_add(request):
    """
    处理管理员添加新班级的请求（网页端）。
    """
    if request.method == "GET":
        return render(request,  "class_add.html")
    name = request.POST.get('name')
    className.objects.create(name=name)
    return render(request, 'user_list.html')

@admin_required
def user_delete(request, user_id):
    """
    处理管理员删除用户的请求。
    """
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, '用户删除成功')
    return redirect('user_list')

@admin_required
def user_edit(request, user_id):
    """
    处理管理员编辑用户信息的请求（网页端）。
    """
    user = get_object_or_404(User, id=user_id)  # 获取要编辑的用户
    logger.info(f'正在编辑 {user.username} 的数据')
    
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
        class_in_id = request.POST.get('classInfo')

        try:
            # 更新用户字段
            user.wx_nickName = nickname # 修正字段名
            user.username = username
            
            # 只有当输入了密码时才更新，且使用 set_password 加密
            if password and password.strip():
                user.set_password(password)
            
            user.phone = int(phone) if phone else None
            user.gender = int(gender) if gender else None
            
            # 处理用户属性和权限
            if user_attribute:
                new_attribute = int(user_attribute)
                # 权限检查：防止非超管提权为超管
                if new_attribute == 4 and request.user.user_attribute != 4:
                    messages.error(request, "只有超级管理员可以设置超级管理员权限。")
                    return redirect('user_list')
                
                user.user_attribute = new_attribute
                user.is_staff = new_attribute in (3, 4)
            
            # 保存基本信息
            user.save()

            # 处理班级关联 (M2M)
            if class_in_id:
                selected_class = className.objects.get(id=class_in_id)
                user.class_in.set([selected_class]) # 使用 set 方法更新 M2M
            else:
                user.class_in.clear() # 如果未选择，清空班级

            logger.info(f'用户 {user.username} 信息更新成功')
            messages.success(request, '用户信息更新成功')
            return redirect('user_list')  # 重定向到列表页

        except ValueError as e:
            logger.error(f"输入数据格式错误：{str(e)}")
            messages.error(request, f"输入数据格式错误：{str(e)}")
        except className.DoesNotExist:
            logger.error("所选班级不存在")
            messages.error(request, "所选班级不存在")
        except Exception as e:
            logger.error(f"更新用户 {user.id} 失败: {e}")
            messages.error(request, f"更新失败：{str(e)}")
            
        # 如果发生错误，重新渲染页面
        return render(request, "user_edit.html", {
            'user': user,
            'class_list': className.objects.all()
        })

@csrf_exempt
@jwt_login_required
def wx_user_edit(request, user_id):
    """
    处理微信小程序端用户编辑自己信息的请求。
    """
    user = get_object_or_404(User, id=user_id)
    if request.method == "GET":
        classNameList = className.objects.all().values('id', 'name')
        class1user = [
            {
                'id': c.id,
                'name': c.name,
            }
            for c in user.class_in.all()
        ]
        response_data = {
            'user': {
                'username': user.username,
                'wx_nickName': user.wx_nickName,
                'wx_avatar': user.wx_avatar,
                'gender': user.gender,
                'user_attribute': user.user_attribute,
                'class_in':class1user,
                'phone': user.phone,
                'last_login_time': user.last_login_time
            },
            'classNameList': list(classNameList)
        }
        return JsonResponse(response_data)
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            logger.info('收到了用户发送的数据：%s',data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)

        if 'gender' in data:
            user.gender = data['gender']
        if 'attribute' in data:
            user.user_attribute = data['attribute']
        if 'phone' in data:
            user.phone = data['phone']
        if 'nickName' in data:
            user.wx_nickName = data['nickName']
        if 'avatarUrl' in data:
            user.wx_avatar = data['avatarUrl']
        if 'class_in_id' in data:
            try:
                selected_class = className.objects.get(id=data['class_in_id'])
                user.class_in.set([selected_class])
            except className.DoesNotExist:
                return JsonResponse({'error': '班级不存在'}, status=400)
        user.save()
        class1user = [
            {
                'id': c.id,
                'name': c.name,
            }
            for c in user.class_in.all()
        ]
        response_data = {
            'user': {
                'username': user.username,
                'wx_nickName': user.wx_nickName,
                'wx_avatar': user.wx_avatar,
                'gender': user.gender,
                'user_attribute': user.user_attribute,
                'class_in':class1user,
                'phone': user.phone,
                'last_login_time': user.last_login_time
            }
        }
        return JsonResponse(response_data)

def user_register(request):
    """
    处理用户的公开注册请求（网页端）。
    """
    if request.method == 'GET':
        form = UserAddForm()
        return render(request, 'user_register.html', {'form': form})
    elif request.method == 'POST':
        form = UserAddForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            phone = form.cleaned_data.get('phone')
            gender = form.cleaned_data.get('gender')
            user_attribute = form.cleaned_data.get('user_attribute')
            class_in_id = form.cleaned_data.get('class_in')
            logger.info(username, password, phone, gender, user_attribute, class_in_id)

            if user_attribute >= 3:
                messages.error(request, "权限不足，不可设置该权限。")
                return render(request, 'user_register.html', {'form': form})

            try:
                user = User(
                    username=username,
                    phone=int(phone) if phone else 13500000000,
                    gender=int(gender) if gender is not None else None,
                    user_attribute=user_attribute if user_attribute in(1,2) else 0,
                    is_staff=user_attribute in (3, 4),
                )
                user.set_password(password)
                if class_in_id:
                    user.class_in = class_in_id
                user.save()

                messages.success(request, '用户创建成功！')
                return redirect('user_list')

            except Exception as e:
                messages.error(request, f'创建用户失败：{str(e)}')
                return render(request, 'user_register.html', {'form': form})
        else:
            return render(request, 'user_register.html', {'form': form})

def generate_class_code():
    """
    生成一个唯一的、由6个字符组成的班级邀请码。
    """
    letters = [c for c in string.ascii_uppercase if c not in ["I", "O"]]
    digits = string.digits
    part1 = "".join(random.choice(letters) for _ in range(2))
    part2 = "".join(random.choice(digits) for _ in range(2))
    part3 = "".join(random.choice(letters) for _ in range(2))
    class_code = part1 + part2 + part3
    if className.objects.filter(code=class_code).exists():
        return generate_class_code()
    return class_code

@csrf_exempt
@jwt_login_required
def create_class(request):
    """
    处理微信小程序端创建班级的 API 请求。
    """
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持 POST 请求'}, status=405)
    
    if request.user.user_attribute < 2:
        return JsonResponse({'error': '权限不足：只有老师可以创建班级'}, status=403)

    try:
        data = json.loads(request.body)
        class_name = data.get('name', '').strip()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': '无效的 JSON 格式'}, status=400)
    
    if not class_name:
        return JsonResponse({'error': '班级名称不能为空'}, status=400)
    
    try:
        class_code = generate_class_code()
    except Exception as e:
        return JsonResponse({'error': '生成班级码失败'}, status=500)
    
    try:
        class_obj, created = className.objects.get_or_create(
            name=class_name,
            defaults={
                'code': class_code,
                'created_by': request.user
            }
        )
    except Exception as e:
        return JsonResponse({'error': '创建班级失败'}, status=500)

    if not created:
        request.user.class_in.add(class_obj)
        message = '班级已存在，已成功加入'
    else:
        request.user.class_in.add(class_obj)
        message = '班级创建成功并已加入'

    try:
        user_classes = [
            {
                'id': c.id,
                'name': c.name,
                'created_at': c.created_at.isoformat() if c.created_at else None,
                'created_by': c.created_by.username if c.created_by else None,
                'code': c.code
            }
            for c in request.user.class_in.all()
        ]
    except Exception as e:
        user_classes = []

    return JsonResponse({
        'success': True,
        'message': message,
        'current_class': {
            'id': class_obj.id,
            'name': class_obj.name,
            'code': class_obj.code
        },
        'user_classes': user_classes
    })

@jwt_login_required
def class_detail(request, class_id):
    """
    获取指定班级的详细信息（微信小程序端 API）。
    """
    if request.method == 'GET':
        c = className.objects.get(id=class_id)
        if not c.code:
            c.code = generate_class_code()
            c.save()
        thisClass = {
            'id': c.id,
            'name': c.name,
            'code': c.code,
            'created_by_id':c.created_by.id,
            'created_by_name':c.created_by.wx_nickName,
            'created_at':c.created_at,
            'studentCount':c.members.count(),
        }
        return JsonResponse({'data':thisClass}, status=200)

@csrf_exempt
@jwt_login_required
def userAddClass(request):
    """
    处理学生通过班级码加入班级的 API 请求。
    """
    if request.method !="POST":
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        data = json.loads(request.body)
        class_code=data.get('class_code','').strip().upper()
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON格式'}, status=400)
    if not class_code:
        return JsonResponse({'error': '班级码不能为空'}, status=400)
    
    student = request.user
    
    if student.user_attribute != 1:
        return JsonResponse({'error': '只有学生可加入班级'}, status=403)
        
    try:
        target_class = className.objects.get(code=class_code)
    except className.DoesNotExist:
        return JsonResponse({'error': '班级码无效，未找到班级'}, status=404)
        
    if target_class in student.class_in.all():
        return JsonResponse({'error': '你已加入该班级'}, status=400)
        
    student.class_in.add(target_class)
    student.save()
    
    return JsonResponse({
        'success': True,
        'message': f'成功加入班级：{target_class.name}',
        'class_info': {
            'id': target_class.id,
            'name': target_class.name,
            'code': target_class.code
        }
    }, status=200)

@jwt_login_required
def get_class_members(request, class_id):
    """
    获取指定班级的成员列表。
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method Not Allowed'}, status=405)

    try:
        target_class = className.objects.get(id=class_id)
        
        members = target_class.members.all().values('id', 'wx_nickName', 'wx_avatar', 'username')
        member_list = []
        for m in members:
            member_list.append({
                'id': m['id'],
                'name': m['wx_nickName'] or m['username'],
                'avatar': m['wx_avatar']
            })

        return JsonResponse({'data': member_list}, status=200)

    except className.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)

class UserProfileUpdateView(generics.UpdateAPIView):
    """
    用户更新个人信息的API视图
    """
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        # 始终返回当前登录用户
        return self.request.user
        
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            "message": "个人信息更新成功",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
