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
    """
    一个装饰器，用于限制只有管理员才能访问特定的视图。

    该装饰器检查当前登录的用户是否经过身份验证，以及其 `user_attribute` 是否
    大于等于3。如果用户未登录，将被重定向到登录页面。如果用户权限不足，
    将显示一条错误消息并重定向到问题列表页面。

    Args:
        view_func (function): 需要被装饰的视图函数。

    Returns:
        function: 包装后的视图函数，增加了权限检查逻辑。

    Example:
        @admin_required
        def admin_dashboard(request):
            # 只有管理员能看到这个视图
            return render(request, 'admin/dashboard.html')
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
    处理微信小程序登录请求，通过前端发送的临时 code 换取微信用户的 openid，
    并为用户生成或获取账户，最终返回 JWT (JSON Web Token) 用于后续的 API 认证。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。
            - method: 必须是 'POST'。
            - body: 包含一个 JSON 对象，格式为 `{"code": "用户的临时登录凭证"}`。

    Returns:
        JsonResponse:
            - 成功时: 返回一个包含 `access` token、`refresh` token 和 `user_id` 的 JSON 对象。
              状态码为 200。
              `{'refresh': '...', 'access': '...', 'user_id': ...}`
            - 失败时: 返回一个包含错误信息的 JSON 对象。
              状态码可能为 400 (请求错误), 401 (认证失败), 405 (方法不允许), 500 (服务器内部错误)。

    Raises:
        json.JSONDecodeError: 如果请求体不是有效的 JSON 格式。
        Exception: 在请求微信 API 或数据库操作过程中可能发生其他未知异常。

    Logic:
        1.  验证请求方法是否为 POST。
        2.  从请求体中解析 JSON 数据，获取 `code`。
        3.  使用 `code`、`appid` 和 `secret` 调用微信 `jscode2session` API，换取 `openid`。
        4.  如果微信 API 返回错误，则记录日志并返回错误信息。
        5.  使用获取到的 `openid` 在数据库中查找或创建一个 `User` 对象。
            - 如果用户是首次登录，会创建一个新用户，并使用 `openid` 作为默认用户名。
        6.  使用 `rest_framework_simplejwt` 为该用户生成 `RefreshToken` 和 `AccessToken`。
        7.  返回生成的 tokens 和用户 ID。

    Example:
        // 前端使用 JavaScript 发起请求
        fetch('/api/wx_login/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: 'some-code-from-wx.login()' })
        })
        .then(response => response.json())
        .then(data => {
            if (data.access) {
                console.log('登录成功, Access Token:', data.access);
                // 保存 token 用于后续请求
            } else {
                console.error('登录失败:', data.error);
            }
        });
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
    """
    处理网页端用户的登录请求。

    该视图函数使用 Django 内置的 `AuthenticationForm` 来验证用户提交的用户名和密码。
    如果验证成功，用户将被登录并重定向到他们之前尝试访问的页面或默认的用户列表页面。
    如果验证失败，将显示相应的错误信息。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。
            - method: 'GET' 或 'POST'。
            - POST: 包含 'username' 和 'password' 的表单数据。
            - GET: 'next' 参数（可选），指定登录后重定向的 URL。

    Returns:
        HttpResponse:
            - 登录成功时: 返回一个 `HttpResponseRedirect` 对象，重定向到目标页面。
            - GET 请求或登录失败时: 返回一个 `HttpResponse` 对象，渲染 `login.html` 模板，
              其中包含登录表单和可能的错误信息。

    Logic:
        1.  如果请求是 POST 方法，则处理表单提交。
            a.  使用 `AuthenticationForm` 验证 `request.POST` 中的数据。
            b.  如果表单有效，使用 `authenticate()` 函数验证用户名和密码。
            c.  如果 `authenticate()` 返回一个用户对象，则表示验证成功。
                - 调用 `login()` 函数为用户创建会话。
                - 重定向到 `next` URL 参数指定的页面，如果不存在则默认为 'user_list'。
            d.  如果 `authenticate()` 返回 `None`，则表示用户名或密码错误，添加错误消息。
        2.  如果请求是 GET 方法，则创建一个空的 `AuthenticationForm`。
        3.  渲染 `login.html` 模板，并将表单实例传递给它。

    Example:
        # urls.py
        path('login/', views.login_view, name='login')

        # template.html (form part)
        <form method="post" action="{% url 'login' %}">
            {% csrf_token %}
            {{ form.as_p }}
            <button type="submit">登录</button>
        </form>
    """
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
def logout_view(request):
    """
    处理用户的注销请求。

    调用 Django 内置的 `logout()` 函数来清除用户的会session信息，
    然后将用户重定向到登录页面。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。

    Returns:
        HttpResponseRedirect: 重定向到名为 'login' 的 URL。

    Side Effects:
        - 清除当前用户的会话数据。
        - 将 `request.user` 设置为 `AnonymousUser` 实例。

    Example:
        # urls.py
        path('logout/', views.logout_view, name='logout')

        # template.html
        <a href="{% url 'logout' %}">退出登录</a>
    """
    logout(request)
    # request.user.is_authenticated = False
    # 注销后重定向到登录页面
    return redirect('login')
@admin_required
def user_list(request):
    """
    显示所有用户的列表页面。

    此视图受 `@admin_required` 装饰器保护，只有管理员才能访问。
    它从数据库中获取所有 `User` 对象，并将其渲染到 `user_list.html` 模板中。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。

    Returns:
        HttpResponse: 渲染后的用户列表页面，其中上下文包含一个名为 `queryset`
                      的变量，其值为所有用户的 QuerySet。

    Example:
        # urls.py
        path('users/', views.user_list, name='user_list')

        # user_list.html (template)
        <table>
            <thead>
                <tr>
                    <th>用户名</th>
                    <th>邮箱</th>
                </tr>
            </thead>
            <tbody>
                {% for user in queryset %}
                <tr>
                    <td>{{ user.username }}</td>
                    <td>{{ user.email }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    """
    queryset = User.objects.all()
    return render(request, "user_list.html", {'queryset': queryset})
@jwt_login_required
def wx_user_list(request, user_id):
    """
    为微信小程序端提供指定用户的详细信息。

    此视图受 `@jwt_login_required` 装饰器保护，需要有效的 JWT Token 才能访问。
    它接收一个 `user_id`，然后调用 `serializeUserInfo` 辅助函数来序列化
    该用户的信息，并以 JSON 格式返回。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。
        user_id (int): 需要查询的用户的 ID。

    Returns:
        JsonResponse:
            - 成功时: 返回一个包含用户信息的 JSON 对象，格式为 `{'data': {...}}`。
              状态码为 200。
            - 如果用户不存在: `serializeUserInfo` 内部可能会处理或引发异常，
              但在此视图中，通常依赖于 `get_object_or_404`（如果使用的话）
              或序列化器返回空。

    Logic:
        1.  接收 `user_id` 作为 URL 参数。
        2.  调用 `serializeUserInfo(user_id)` 来获取用户的序列化数据。
        3.  将序列化后的数据包装在 `{'data': ...}` 结构中。
        4.  返回一个 `JsonResponse`。

    Example:
        // 前端请求
        GET /api/wx/user/123/

        // 成功响应
        {
            "data": {
                "username": "testuser",
                "wx_nickName": "微信昵称",
                // ... 其他用户信息
            }
        }
    """
    data = serializeUserInfo(user_id)
    logger.info('发送用户数据：%s',data)
    return JsonResponse({'data': data}, status=200)  # 直接返回单个对象
@admin_required
def user_add(request):
    """
    处理管理员在网页端添加新用户的请求。

    此视图受 `@admin_required` 装饰器保护。
    - 对于 GET 请求，它显示一个用于添加新用户的空表单 (`UserAddForm`)。
    - 对于 POST 请求，它接收并验证表单数据。如果数据有效，则创建一个新用户，
      显示成功消息，并重定向到用户列表页面。如果数据无效，则重新显示
      表单及错误信息。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。
            - method: 'GET' 或 'POST'。
            - POST: 包含新用户信息的表单数据。

    Returns:
        HttpResponse:
            - 成功添加用户后: 返回一个 `HttpResponseRedirect` 对象，重定向到用户列表。
            - GET 请求或表单无效时: 返回一个 `HttpResponse` 对象，渲染 `user_add.html`
              模板，其中包含 `UserAddForm` 实例。

    Logic:
        1.  检查请求方法。
        2.  如果是 POST 请求：
            a.  使用 `request.POST` 数据实例化 `UserAddForm`。
            b.  调用 `form.is_valid()` 进行验证。
            c.  如果有效，调用 `form.save()` 创建用户（该方法在 `UserAddForm` 中被重写
                以正确处理密码）。
            d.  添加成功消息并重定向。
        3.  如果是 GET 请求：
            a.  创建一个空的 `UserAddForm` 实例。
        4.  渲染 `user_add.html` 模板，并将表单实例传递给它。

    Example:
        # urls.py
        path('user/add/', views.user_add, name='user_add')
    """
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
    """
    处理管理员添加新班级的请求（网页端）。

    此视图受 `@admin_required` 装饰器保护。
    - 对于 GET 请求，显示一个用于输入班级名称的表单。
    - 对于 POST 请求，从表单中获取班级名称，创建一个新的 `className` 对象，
      然后重定向到用户列表页面。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。
            - method: 'GET' 或 'POST'。
            - POST: 包含 'name' 字段的表单数据，值为班级名称。

    Returns:
        HttpResponse:
            - GET 请求时: 渲染 `class_add.html` 模板。
            - POST 请求时: 渲染 `user_list.html` 模板（但在实践中，重定向到班级列表页通常更佳）。

    Logic:
        1.  如果请求是 GET 方法，渲染班级添加页面。
        2.  如果请求是 POST 方法，获取 POST 数据中的 `name`。
        3.  使用获取的 `name` 创建一个新的 `className` 记录。
        4.  渲染用户列表页面作为响应。

    Example:
        # urls.py
        path('class/add/', views.class_add, name='class_add')
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

    此视图受 `@admin_required` 装饰器保护。
    它通过 `user_id` 查找指定的用户，如果找到则将其从数据库中删除。
    操作完成后，会添加一条成功消息，并重定向回用户列表页面。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。
        user_id (int): 要删除的用户的 ID。

    Returns:
        HttpResponseRedirect: 重定向到名为 'user_list' 的 URL。

    Raises:
        Http404: 如果根据 `user_id` 未找到任何用户。

    Logic:
        1.  使用 `get_object_or_404` 安全地获取 `User` 对象，如果找不到则自动返回 404 页面。
        2.  调用用户的 `delete()` 方法将其删除。
        3.  使用 `messages.success()` 添加一条成功反馈信息。
        4.  重定向到用户列表页面。

    Example:
        # urls.py
        path('user/delete/<int:user_id>/', views.user_delete, name='user_delete')

        # template.html
        <a href="{% url 'user_delete' user.id %}">删除</a>
    """
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, '用户删除成功')
    return redirect('user_list')
@admin_required
def user_edit(request, user_id):
    """
    处理管理员编辑用户信息的请求（网页端）。

    此视图受 `@admin_required` 装饰器保护。
    - 对于 GET 请求，显示一个预填充了当前用户信息的表单，以及一个包含所有班级的下拉列表。
    - 对于 POST 请求，接收并验证提交的表单数据，然后更新对应的 `User` 对象。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。
            - method: 'GET' 或 'POST'。
            - POST: 包含用户更新信息的表单数据。
        user_id (int): 正在被编辑的用户的 ID。

    Returns:
        HttpResponse:
            - GET 请求或更新失败时: 渲染 `user_edit.html` 模板，上下文包含 `user` 和 `class_list`。
            - 成功更新后: 返回一个 `HttpResponseRedirect` 对象，重定向到用户列表页面。

    Raises:
        Http404: 如果根据 `user_id` 未找到任何用户。

    Logic:
        1.  使用 `get_object_or_404` 获取要编辑的用户对象。
        2.  如果是 GET 请求，获取所有班级列表，并渲染 `user_edit.html` 模板，
            将 `user` 和 `class_list` 传递给模板。
        3.  如果是 POST 请求，从 `request.POST` 中提取所有相关字段。
        4.  进行权限检查：非超级管理员不能将其他用户提升为超级管理员。
        5.  在一个 `try...except` 块中更新用户对象的属性。
            - 对 `phone` 和 `gender` 进行类型转换。
            - 根据 `user_attribute` 设置 `is_staff` 标志。
            - 如果提供了 `class_in_id`，则获取并关联 `className` 对象。
            - 调用 `user.save()` 保存更改。
        6.  如果更新成功，添加成功消息并重定向到用户列表。
        7.  如果发生 `ValueError`（如类型转换失败）或 `className.DoesNotExist`（班级不存在）
            等异常，记录错误并重新渲染编辑页面，同时显示错误信息。

    Example:
        # urls.py
        path('user/edit/<int:user_id>/', views.user_edit, name='user_edit')
    """
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
@jwt_login_required
def wx_user_edit(request, user_id):
    """
    处理微信小程序端用户编辑自己信息的请求。

    此视图受 `@jwt_login_required` 装饰器保护，需要有效的 JWT Token。
    它同时处理 GET 和 POST 请求，用于获取和更新用户信息。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。
            - method: 'GET' 或 'POST'。
            - POST body: 包含要更新的用户信息的 JSON 对象。例如：
              `{"gender": 1, "phone": "1234567890", "class_in_id": 5}`
        user_id (int): 正在编辑的用户的 ID。

    Returns:
        JsonResponse:
            - GET 请求时: 返回包含用户当前信息和所有班级列表的 JSON 对象。
            - POST 请求时: 更新用户信息后，返回更新后的用户信息 JSON 对象。
            - 失败时: 返回包含错误信息的 JSON 对象，状态码可能为 400 (无效请求) 或 404 (未找到)。

    Raises:
        Http404: 如果根据 `user_id` 未找到用户。
        json.JSONDecodeError: 如果 POST 请求的 body 不是有效的 JSON。
        className.DoesNotExist: 如果 POST 请求中提供的 `class_in_id` 无效。

    Logic:
        1.  使用 `get_object_or_404` 获取用户对象。
        2.  如果是 GET 请求：
            a.  获取所有班级的 ID 和名称。
            b.  获取用户当前所在的班级信息。
            c.  构建包含用户详细信息和班级列表的响应数据。
            d.  返回 `JsonResponse`。
        3.  如果是 POST 请求：
            a.  解析请求体中的 JSON 数据。
            b.  根据 JSON 数据中存在的键，逐一更新用户对象的属性（如 `gender`, `phone`, `wx_nickName` 等）。
            c.  如果提供了 `class_in_id`，查找对应的班级并更新用户的班级关联（使用 `set()` 方法替换当前班级）。
            d.  调用 `user.save()` 保存更改。
            e.  构建并返回包含更新后用户信息的 `JsonResponse`。

    Example:
        // GET 请求获取用户信息
        GET /api/wx/user/edit/123/

        // POST 请求更新用户信息
        POST /api/wx/user/edit/123/
        Body: {
            "nickName": "新的微信昵称",
            "gender": 1,
            "class_in_id": 2
        }
    """
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

def user_register(request):
    """
    处理用户的公开注册请求（网页端）。

    该视图允许任何人通过网页表单注册一个新账户。
    - 对于 GET 请求，显示一个空的注册表单 (`UserAddForm`)。
    - 对于 POST 请求，验证表单数据。如果有效，则创建一个新用户并重定向到登录页面。
      注册时会进行权限检查，防止用户将自己注册为管理员。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。
            - method: 'GET' 或 'POST'。
            - POST: 包含新用户注册信息的表单数据。

    Returns:
        HttpResponse:
            - 成功注册后: 返回一个 `HttpResponseRedirect` 对象，重定向到用户列表页面。
            - GET 请求或表单无效时: 返回一个 `HttpResponse` 对象，渲染 `user_register.html`
              模板，其中包含 `UserAddForm` 实例和可能的错误信息。

    Logic:
        1.  如果是 GET 请求，显示一个空的 `UserAddForm`。
        2.  如果是 POST 请求：
            a.  使用 `request.POST` 数据实例化 `UserAddForm`。
            b.  如果表单有效，提取经过验证的数据。
            c.  进行权限检查：确保 `user_attribute` 不被设置为管理员级别 (>=3)。
            d.  在一个 `try...except` 块中创建新的 `User` 对象。
                - 使用 `set_password()` 方法安全地加密密码。
                - 根据 `user_attribute` 设置 `is_staff`。
                - 关联班级（如果提供）。
                - 保存用户对象。
            e.  如果创建成功，添加成功消息并重定向。
            f.  如果创建失败，添加错误消息并重新渲染注册表单。
        3.  如果表单验证失败，重新渲染带有错误的注册表单。

    Example:
        # urls.py
        path('register/', views.user_register, name='register')
    """
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
    """
    生成一个唯一的、由6个字符组成的班级邀请码。

    班级码的格式为 `LLDDLL`，其中 `L` 是一个大写字母（排除 'I' 和 'O'），
    `D` 是一个数字。该函数会确保生成的班级码在数据库中是唯一的，如果生成
    的码已存在，则会递归调用自身直到生成一个唯一的码。

    Args:
        None

    Returns:
        str: 一个唯一的6位班级码。

    Logic:
        1.  定义字母和数字的字符集。字母集排除了容易混淆的 'I' 和 'O'。
        2.  随机生成两段两个字母和一段两个数字的组合。
        3.  拼接成 `LLDDLL` 格式的班级码。
        4.  查询数据库检查该班级码是否已存在 (`className.objects.filter(code=...).exists()`)。
        5.  如果已存在，则递归调用 `generate_class_code()` 重新生成。
        6.  如果不存在，则返回这个唯一的班级码。

    Example:
        new_code = generate_class_code()
        print(new_code)  # 输出, e.g., "AB12CD"
    """
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
    """
    处理微信小程序端创建班级的 API 请求。

    此视图受 `@jwt_login_required` 保护。它接收一个包含班级名称的 POST 请求，
    然后创建或获取一个班级。如果班级是新创建的，会为其生成一个唯一的班级码。
    无论班级是新建还是已存在，当前用户都会被加入到该班级中。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。
            - method: 必须是 'POST'。
            - body: 包含班级信息的 JSON 对象，格式为 `{"name": "班级名称"}`。

    Returns:
        JsonResponse:
            - 成功时: 返回一个包含成功消息、当前班级信息和用户所有班级列表的 JSON 对象。
              状态码为 200。
            - 失败时: 返回包含错误信息的 JSON 对象，状态码可能为 400, 405, 或 500。

    Logic:
        1.  验证请求方法是否为 POST。
        2.  解析请求体中的 JSON 数据，获取 `class_name`。
        3.  调用 `generate_class_code()` 生成一个唯一的班级码。
        4.  使用 `className.objects.get_or_create()` 尝试创建或获取班级。
            - `name` 是查找条件。
            - `code` 和 `created_by` 是只在创建新对象时使用的默认值。
        5.  如果班级是新创建的 (`created` is True)，用户自动加入。
        6.  如果班级已存在 (`created` is False)，也将用户加入（如果尚未加入）。
        7.  获取用户当前加入的所有班级列表，并进行序列化。
        8.  构建并返回一个包含操作结果、当前班级信息和用户所有班级列表的 `JsonResponse`。

    Example:
        // POST 请求创建新班级
        POST /api/class/create/
        Body: {"name": "三年二班"}

        // 成功响应
        {
            "success": true,
            "message": "班级创建成功并已加入",
            "current_class": {"id": 1, "name": "三年二班", "code": "XY34ZQ"},
            "user_classes": [...]
        }
    """
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
    """
    获取指定班级的详细信息（微信小程序端 API）。

    此视图受 `@jwt_login_required` 保护。它接收一个 `class_id`，然后返回该班级的
    详细信息，包括班级码、创建者信息和学生数量。如果班级还没有班级码，
    会在此次请求中为其生成并保存一个。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象 (仅处理 GET)。
        class_id (int): 需要查询的班级的 ID。

    Returns:
        JsonResponse:
            - 成功时: 返回一个包含班级详细信息的 JSON 对象，格式为 `{'data': {...}}`。
              状态码为 200。
            - 如果班级不存在: 会引发 `className.DoesNotExist` 异常，导致服务器 500 错误，
              除非有中间件处理。

    Logic:
        1.  验证请求方法是否为 GET。
        2.  通过 `class_id` 获取 `className` 对象。
        3.  检查该班级是否已有 `code`。如果没有，则调用 `generate_class_code()` 生成一个并保存。
        4.  构建一个包含班级详细信息的字典，包括 ID, 名称, 班级码, 创建者信息和成员数量。
        5.  将该字典包装在 `{'data': ...}` 结构中并作为 `JsonResponse` 返回。

    Example:
        // GET 请求获取班级详情
        GET /api/class/detail/1/

        // 成功响应
        {
            "data": {
                "id": 1,
                "name": "三年二班",
                "code": "AB12CD",
                "created_by_id": 5,
                "created_by_name": "张老师",
                "created_at": "2023-10-27T10:00:00Z",
                "studentCount": 30
            }
        }
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
        return JsonResponse({'data':thisClass}, status=200)  # 直接返回单个对象
#学生加入班级
@csrf_exempt
@jwt_login_required
def userAddClass(request):
    """
    处理学生通过班级码加入班级的 API 请求。

    此视图受 `@jwt_login_required` 保护。它接收一个包含 `userId` 和 `class_code`
    的 POST 请求。在验证用户身份（必须是学生）和班级码有效性之后，
    将该学生添加到对应的班级中。

    Args:
        request (HttpRequest): Django 的 HTTP 请求对象。
            - method: 必须是 'POST'。
            - body: 包含用户 ID 和班级码的 JSON 对象，格式为
              `{"userId": "...", "class_code": "..."}`。

    Returns:
        JsonResponse:
            - 成功时: 返回成功消息和加入的班级信息，状态码 200。
            - 失败时: 返回具体的错误信息，状态码可能为 400, 403, 404, 或 405。

    Logic:
        1.  验证请求方法是否为 POST。
        2.  解析请求体中的 JSON 数据，获取 `userId` 和 `class_code`。
        3.  验证 `class_code` 是否为空。
        4.  根据 `userId` 获取学生对象，并验证其 `user_attribute` 是否为 1 (学生)。
        5.  根据 `class_code` (转换为大写) 查找目标班级。
            - 如果找不到，返回 404 错误。
        6.  检查学生是否已经加入了该班级，防止重复加入。
        7.  如果所有验证通过，将学生添加到班级的 `members` 中（通过 `student.class_in.add()`）。
        8.  保存学生对象。
        9.  返回成功的 `JsonResponse`，包含成功消息和班级信息。

    Example:
        // POST 请求加入班级
        POST /api/user/add-class/
        Body: {"userId": 10, "class_code": "AB12CD"}

        // 成功响应
        {
            "success": true,
            "message": "成功加入班级：三年二班",
            "class_info": {"id": 1, "name": "三年二班", "code": "AB12CD"}
        }
    """
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

