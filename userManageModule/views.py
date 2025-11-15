from functools import wraps
import requests
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken
from IntelligentHomeworkGradingSystem import settings
from .decorators import jwt_login_required
from .forms import UserAddForm
from .models import User
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
import logging
import string
import random
from userManageModule.serializers import serializeUserInfo
logger = logging.getLogger(__name__)
#登录验证
def admin_required(view_func):
    """自定义装饰器：仅允许管理员（user_attribute >= 3）访问"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_attribute < 3:
            logger.info(request.user.username,'没有权限访问该页面')
            messages.error(request, "您没有权限访问该页面。")
            return redirect('question_list')  # 或重定向到首页
        return view_func(request, *args, **kwargs)
    return _wrapped_view
@csrf_exempt  # API 接口需要禁用 CSRF 保护
def wx_login(request):
    """
    [修改后] 小程序登录：用 code 换取 access 和 refresh token
    """
    # --- 修正问题一：解析 JSON 数据 ---
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

    # 调用微信接口换取 openid (这部分逻辑不变)
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

        # --- 修正问题二：使用 simplejwt 生成 token ---

        # 根据 openid 查找或创建用户
        user, created = User.objects.get_or_create(
            openid=openid,
            defaults={'username': openid}  # 首次创建时，可以用 openid 作为默认用户名
        )

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
    """处理用户登录请求"""
    # if request.user.is_authenticated:
    #     return redirect('user_list')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # 1. 使用 Django 的标准方式安全地验证用户名和密码
            # 它会自动处理密码哈希的比较，非常安全
            if not username:
                logger.info('username error')
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
            logger.info(form.errors)
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})
# 建议同时添加一个注销视图
def logout_view(request):
    """处理用户注销请求"""
    logout(request)
    # request.user.is_authenticated = False
    # 注销后重定向到登录页面
    return redirect('login')
@admin_required
def user_list(request):
    queryset = User.objects.all()
    return render(request, "user_list.html", {'queryset': queryset})
@jwt_login_required
def wx_user_list(request, user_id):
    data = serializeUserInfo(user_id)
    logger.info('发送用户数据：%s',data)
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
    logger.info('正在编辑',user.username,'的数据')
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
        logger.info(user_attribute)
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
                logger.info(user,"只有超级管理员可以设置超级管理员权限。")
                messages.error(request, "只有超级管理员可以设置超级管理员权限。")
                return redirect('user_list')
            user.is_staff = user_attribute in (3, 4)
            user.class_in = className.objects.get(id=class_in_id) if class_in_id else None
            user.save()  # 保存到数据库
            logger.info(user,'用户信息更新成功')
            messages.success(request, '用户信息更新成功')
            return redirect('user_list')  # 重定向到列表页
        except ValueError as e:
            # 特别处理 int() 转换错误
            logger.info(request, f"输入数据格式错误：{str(e)}")
            return render(request, "user_edit.html", {
                'user': user,
                'class_list': className.objects.all()
            })
        except className.DoesNotExist:
            logger.info(request, "班级不存在")
            return render(request, "user_edit.html", {
                'user': user,
                'class_list': className.objects.all()
            })
        except Exception as e:
            # 记录日志（生产环境用 logging）
            logger.info(f"更新用户 {user.id} 失败: {e}")
            logger.info(request, f"更新失败：{str(e)}")
            return render(request, "user_edit.html", {
                'user': user,
                'class_list': className.objects.all()
            })
@csrf_exempt
@jwt_login_required# 禁用 CSRF 检查（适用于 API 接口）
def wx_user_edit(request, user_id):
    # 获取指定用户
    user = get_object_or_404(User, id=user_id)
    #前端传过来 ： POST / GET -> 提交至后端 / 从后端获取
    if request.method == "GET":
        classNameList = className.objects.all().values('id', 'name')  # 获取所有班级实例
        class1user = [
            {
                'id': c.id,
                'name': c.name,  # 班级名称（空则为None）
            }
            for c in user.class_in.all()
        ]
        response_data = {
            'user': {
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
        # 获取前端传来的数据
        try:
            data = json.loads(request.body)
            logger.info('收到了用户发送的数据：%s',data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        # print('用户要更改为的数据为:',data)
        # logger.info('用户要更改为的数据为:',data)
        # 更新用户数据
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
                user.class_in.set([selected_class])  # 替换为仅包含这一个班级
            except className.DoesNotExist:
                return JsonResponse({'error': '班级不存在'}, status=400)
        user.save()
        class1user = [
            {
                'id': c.id,
                'name': c.name,  # 班级名称（空则为None）
            }
            for c in user.class_in.all()
        ]
        response_data = {
            'user': {
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
# @api_view(['POST'])
# @permission_classes([AllowAny])
# @admin_required
# def wechat_login(request):
#     """微信小程序登录接口 - 函数视图实现"""
#     code = request.data.get('code')  # 从前端获取code
#     nickName = request.data.get('nickName')  # 从前端获取nickName
#     avatarUrl = request.data.get('avatarUrl')  # 从前端获取avatarUrl
#     if not code:
#         logger.info("登录请求缺少code参数")  # 记录警告日志
#         return Response({'error': '缺少code参数'}, status=status.HTTP_400_BAD_REQUEST)
#
#     # 读取微信配置（提前检查配置是否存在）
#     appid = getattr(settings, 'WECHAT_APPID', None)
#     secret = getattr(settings, 'WECHAT_SECRET', None)
#     if not appid or not secret:
#         logger.info("微信登录配置缺失：WECHAT_APPID或WECHAT_SECRET未设置")
#         return Response({'error': '服务器配置错误'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#
#     # 微信code2Session接口URL
#     url = f'https://api.weixin.qq.com/sns/jscode2session?appid={appid}&secret={secret}&js_code={code}&grant_type=authorization_code'
#
#     try:
#         # 调用微信接口，设置超时时间（避免请求挂起）
#         response = requests.get(url, timeout=10)  # 超时时间10秒
#         response.raise_for_status()  # 触发HTTP错误（如404、500）
#         response_data = response.json()
#
#         # 处理微信接口返回的错误
#         if 'errcode' in response_data and response_data['errcode'] != 0:
#             err_msg = response_data.get('errmsg', '未知错误')
#             logger.info(f"微信code2Session失败：errcode={response_data['errcode']}, errmsg={err_msg}")
#             return Response({
#                 'error': '微信登录失败',
#                 'detail': err_msg,
#                 'errcode': response_data['errcode']  # 返回微信错误码，便于调试
#             }, status=status.HTTP_400_BAD_REQUEST)
#
#         # 提取关键信息
#         openid = response_data.get('openid')
#         session_key = response_data.get('session_key')
#         if not openid or not session_key:
#             logger.info(f"微信接口未返回openid或session_key：{response_data}")
#             return Response({'error': '获取用户身份失败'}, status=status.HTTP_400_BAD_REQUEST)
#
#         # 数据库操作（单独捕获数据库异常）
#         try:
#             user, created = User.objects.get_or_create(openid=openid)
#             user.session_key = session_key  # 确保User模型有session_key字段
#             user.wx_nickName = nickName
#             user.wx_avatar = avatarUrl
#             user.save(update_fields=['session_key','wx_nickName','wx_avatar'])  # 只更新需要的字段，提高性能
#         except Exception as e:
#             logger.info(f"用户创建/更新失败：{str(e)}")  # 记录堆栈信息
#             return Response({'error': '用户信息存储失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#
#         # 生成JWT（单独捕获JWT相关异常）
#         try:
#             refresh = RefreshToken.for_user(user)
#         except Exception as e:
#             logger.info(f"JWT令牌生成失败：{str(e)}")
#             return Response({'error': '认证令牌生成失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#
#         # 登录成功，记录日志
#         logger.info(f"用户登录成功：openid={openid}, 用户ID={user.id}, 新用户={created}")
#         return Response({
#             'refresh': str(refresh),
#             'access': str(refresh.access_token),
#             'user_id': user.id,
#             'is_new_user': created,
#             'code':200
#         }, status=status.HTTP_200_OK)
#
#     # 细分异常类型
#     except requests.exceptions.Timeout:
#         logger.info("调用微信接口超时")
#         return Response({'error': '微信接口响应超时'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
#     except requests.exceptions.RequestException as e:  # 网络错误（如连接失败、HTTP 500）
#         logger.info(f"微信接口网络请求失败：{str(e)}")
#         return Response({'error': '微信接口请求失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#     except Exception as e:  # 其他未捕获异常
#         logger.info(f"登录接口未知错误：{str(e)}")
#         return Response({'error': '服务器内部错误'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
def user_register(request):
    if request.method == 'GET':
        # if(request.user.is_authenticated):
        #     return redirect('user_list')
        form = UserAddForm()  # 不传 request.POST！GET 时是空表单
        return render(request, 'user_register.html', {'form': form})
    elif request.method == 'POST':
        form = UserAddForm(request.POST)
        if form.is_valid():
            # 获取干净的数据
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
                # 创建新用户（不是更新！）
                user = User(
                    username=username,
                    phone=int(phone) if phone else 13500000000,
                    gender=int(gender) if gender is not None else None,
                    user_attribute=user_attribute if user_attribute in(1,2) else 0,
                    is_staff=user_attribute in (3, 4),  # 管理员和超级管理员有后台权限
                )
                user.set_password(password)  # ✅ 正确加密密码！
                if class_in_id:
                    user.class_in = class_in_id  # 注意：如果 class_in 是外键，Django 会自动处理
                user.save()

                messages.success(request, '用户创建成功！')
                return redirect('user_list')

            except Exception as e:
                messages.error(request, f'创建用户失败：{str(e)}')
                return render(request, 'user_register.html', {'form': form})
        else:
            # 表单验证失败，返回带错误信息的表单
            return render(request, 'user_register.html', {'form': form})
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import className  #
#生成班级码
def generate_class_code():
    #letter为大写英文字母,除了I和O;digits为0-9的数字
    letters = [c for c in string.ascii_uppercase if c not in ["I", "O"]]
    digits = string.digits
    #班级码分为三部分
    part1 = "".join(random.choice(letters) for _ in range(2))
    part2 = "".join(random.choice(digits) for _ in range(2))
    part3 = "".join(random.choice(letters) for _ in range(2))
    class_code = part1 + part2 + part3
    # 检查唯一性：若已存在则重新生成
    if className.objects.filter(code=class_code).exists():
        return generate_class_code()
    return class_code
@csrf_exempt
@jwt_login_required
def create_class(request):
    """创建班级接口支持 POST 请求，需要班级名称参数"""
    # 1. 请求方法验证
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持 POST 请求'}, status=405)
    # 2. 请求数据解析和验证
    try:
        data = json.loads(request.body)
        class_name = data.get('name', '').strip()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': '无效的 JSON 格式'}, status=400)
    # 3. 参数验证
    if not class_name:
        return JsonResponse({'error': '班级名称不能为空'}, status=400)
    # 4. 生成唯一班级码
    try:
        class_code = generate_class_code()
    except Exception as e:
        return JsonResponse({'error': '生成班级码失败'}, status=500)
    # 5. 创建或获取班级
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

    # 6. 处理已存在班级的情况
    if not created:
        # 如果班级已存在，将用户加入该班级
        request.user.class_in.add(class_obj)
        message = '班级已存在，已成功加入'
    else:
        # 新创建的班级，用户自动加入
        request.user.class_in.add(class_obj)
        message = '班级创建成功并已加入'

    # 7. 获取用户所有班级信息
    try:
        user_classes = [
            {
                'id': c.id,
                'name': c.name,
                'created_at': c.created_at.isoformat() if c.created_at else None,
                'created_by': c.created_by.username if c.created_by else None,
                'code': c.code  # 包含班级码
            }
            for c in request.user.class_in.all()
        ]
    except Exception as e:
        user_classes = []

    # 8. 返回响应
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
        return JsonResponse({'data':thisClass}, status=200)  # 直接返回单个对象
#学生加入班级
@csrf_exempt
@jwt_login_required
def userAddClass(request):
    if request.method !="POST":
        return JsonResponse({'error': '仅支持POST请求'}, status=405)
    try:
        data = json.loads(request.body)
        userId = data.get('userId','').strip()
        class_code=data.get('class_code','').strip().upper()
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON格式'}, status=400)
    if not class_code:
        return JsonResponse({'error': '班级码不能为空'}, status=400)
    #确认学生存在
    student = User.objects.get(id=userId)
    if student.user_attribute != 1:
        return JsonResponse({'error': '只有学生可加入班级'}, status=403)
    #确认班级码存在
    try:
        #得到目标班级
        target_class = className.objects.get(code=class_code)
    except className.DoesNotExist:
        return JsonResponse({'error': '班级码无效，未找到班级'}, status=404)
    #预防重复加入
    if target_class in student.class_in.all():
        return JsonResponse({'error': '你已加入该班级'}, status=400)
    #保存
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

