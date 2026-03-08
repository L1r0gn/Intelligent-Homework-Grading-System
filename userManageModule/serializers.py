from django.http import JsonResponse
from django.utils import timezone
from .models import User
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

def serializeUserInfo(user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': '用户不存在'}, status=404)
        # 处理关联字段和枚举值转换（关键优化）
    class1user = serializeClassInfo(user_id)
    user.last_login_time = timezone.now()
    user.save()
    data = {
        'id': user.id,
        'uid':user.uid,
        'username': user.username,
        'wx_nickName': user.wx_nickName,
        'wx_avatar': user.wx_avatar,
        'phone': user.phone,
        'gender': user.gender,  # 返回转换后的文本（男/女/None）
        'user_attribute': user.user_attribute,  # 返回转换后的文本（student/teacher/None）
        'class_in':class1user,
        'wx_country': user.wx_country,
        'wx_province': user.wx_province,
        'wx_city': user.wx_city,
        'last_login_time': user.last_login_time.strftime('%Y-%m-%d %H:%M:%S'),  # 格式化时间
        'date_joined': user.date_joined.strftime('%Y-%m-%d'),  # 格式化时间
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
            'grade':c.grade,
            'description':c.description,
            'homeroom_teacher_name':c.homeroom_teacher.wx_nickName if c.homeroom_teacher else None,


        }
        for c in user.class_in.all()
    ]
    return class1user

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    wx_nickName = serializers.CharField(required=False, max_length=128, label='姓名/昵称')
    phone = serializers.IntegerField(required=False, label='手机号')
    email = serializers.EmailField(required=False, label='邮箱')
    gender = serializers.ChoiceField(choices=User.genders_choices, required=False, label='性别')
    
    # Password change fields
    current_password = serializers.CharField(write_only=True, required=False, label='当前密码')
    new_password = serializers.CharField(write_only=True, required=False, label='新密码')
    confirm_password = serializers.CharField(write_only=True, required=False, label='确认新密码')

    class Meta:
        model = User
        fields = ['wx_nickName', 'phone', 'email', 'gender', 'current_password', 'new_password', 'confirm_password']

    def validate_phone(self, value):
        # Basic phone validation (China)
        s_value = str(value)
        if len(s_value) != 11 or not s_value.startswith('1'):
             raise serializers.ValidationError("请输入有效的11位手机号码")
        return value

    def validate(self, data):
        # Check if password change is requested
        if data.get('new_password') or data.get('confirm_password'):
            if not data.get('current_password'):
                raise serializers.ValidationError({"current_password": "修改密码需要提供当前密码"})
            
            # Verify current password
            user = self.instance
            if not user.check_password(data.get('current_password')):
                raise serializers.ValidationError({"current_password": "当前密码不正确"})
            
            # Check if new passwords match
            if data.get('new_password') != data.get('confirm_password'):
                raise serializers.ValidationError({"confirm_password": "两次输入的密码不一致"})
            
            # Validate password strength
            try:
                validate_password(data.get('new_password'), user)
            except DjangoValidationError as e:
                raise serializers.ValidationError({"new_password": list(e.messages)})
                
        return data

    def update(self, instance, validated_data):
        # Handle password update separately
        new_password = validated_data.pop('new_password', None)
        validated_data.pop('confirm_password', None)
        validated_data.pop('current_password', None)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        if new_password:
            instance.set_password(new_password)
            
        instance.save()
        return instance
