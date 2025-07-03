from userManageModule import models
from django.shortcuts import render, redirect  # 新增redirect
from django.contrib import messages


def user_list(request):
    queryset = models.User.objects.all()
    return render(request, "user_list.html", {'queryset': queryset})


def user_add(request):
    if request.method == "GET":
        # 获取所有班级信息，用于表单下拉选择（外键关联需要）
        class_list = models.class_name.objects.all()
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
        gender = int(gender) if gender else None  # 性别转为整数（1/2）
        user_attribute = int(user_attribute) if user_attribute else None  # 属性转为整数（1/2）
        class_in = models.class_name.objects.get(id=class_in_id) if class_in_id else None  # 外键关联班级

        # 创建用户（字段名与模型完全匹配）
        models.User.objects.create(
            nickName=nickName,
            phone=phone,
            gender=gender,
            user_attribute=user_attribute,
            class_in=class_in  # 正确关联外键字段class_in
        )
        messages.success(request, '用户添加成功')
        return render(request,'user_list.html') # 重定向到列表页，避免重复提交

    except Exception as e:
        messages.error(request, f'添加失败: {str(e)}')
        # 回传数据到表单，保留用户输入
        return render(request, 'user_add.html', {
            'nickName': nickName,
            'phone': phone,
            'gender': gender,
            'user_attribute': user_attribute,
            'class_in_id': class_in_id,
            'class_list': models.class_name.objects.all()  # 回传班级列表
        })

def class_add(request):
    if request.method == "GET":
        return render(request,  "class_add.html")
    class_name = request.POST.get('name')
    models.class_name.objects.create(name=class_name)
    return render(request, 'user_list.html')

