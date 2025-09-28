# userManageModule/forms.py

from django import forms
from .models import User, className  # 确保导入 User 和 className 模型
from django.contrib.auth.hashers import make_password


class UserAddForm(forms.ModelForm):
    # 在模型之外，我们额外定义密码和确认密码字段
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput,
        required=True,
        help_text='密码最少8位'
    )
    password_confirm = forms.CharField(
        label='确认密码',
        widget=forms.PasswordInput,
        required=True
    )

    # 我们需要动态地从数据库获取班级列表
    class_in = forms.ModelChoiceField(
        queryset=className.objects.all(),
        label='所属班级',
        required=False,  # 允许不选择班级
        empty_label="-- 请选择班级 --"
    )

    class Meta:
        model = User
        # 定义表单包含模型的哪些字段
        fields = ['username', 'wx_nickName', 'phone', 'gender', 'user_attribute', 'class_in']
        labels = {
            'username': '用户名',
            'wx_nickName': '微信昵称',
            'phone': '手机号',
            'gender': '性别',
            'user_attribute': '用户属性',
        }

    # clean 方法用于自定义全表单的验证逻辑
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            # 如果两次密码不匹配，则引发一个验证错误
            raise forms.ValidationError("两次输入的密码不一致。")

        return cleaned_data

    # 重写save方法，以使用 create_user 来正确处理密码
    def save(self, commit=True):
        # 使用 create_user 方法，它会自动处理密码的哈希加密
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            # 其他字段可以作为关键字参数传入
            wx_nickName=self.cleaned_data['wx_nickName'],
            phone=self.cleaned_data['phone'],
            gender=self.cleaned_data['gender'],
            user_attribute=self.cleaned_data['user_attribute'],
            class_in=self.cleaned_data.get('class_in')  # .get() 更安全
        )
        return user