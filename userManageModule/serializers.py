from django.http import JsonResponse
from .models import User
def serializeUserInfo(user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': '用户不存在'}, status=404)
        # 处理关联字段和枚举值转换（关键优化）
    class1user = serializeClassInfo(user_id)
    data = {
        'id': user.id,
        'wx_nickName': user.wx_nickName,
        'wx_avatar': user.wx_avatar,
        'phone': user.phone,
        'gender': user.gender,  # 返回转换后的文本（男/女/None）
        'user_attribute': user.user_attribute,  # 返回转换后的文本（student/teacher/None）
        'class_in':class1user,
        'wx_country': user.wx_country,
        'wx_province': user.wx_province,
        'wx_city': user.wx_city,
        'last_login_time': user.last_login_time.strftime('%Y-%m-%d %H:%M:%S')  # 格式化时间
    }
    return data

def serializeClassInfo(user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': '用户不存在'}, status=404)
    class1user = [
        {
            'id': c.id,
            'name': c.name,
            'code': c.code,
            'created_by_id':c.created_by.id,
            'created_by_name':c.created_by.wx_nickName,
            'created_at':c.created_at,
            'studentCount':c.members.count(),
        }
        for c in user.class_in.all()
    ]
    return class1user