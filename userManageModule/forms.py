# userManageModule/forms.py

from django import forms
from .models import User, className, ClassTeacher  # 确保导入 User 和 className 模型
import datetime

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

    # 删除班级选择字段
    # class_in = forms.ModelChoiceField(
    #     queryset=className.objects.all(),
    #     label='所属班级',
    #     required=False,  # 允许不选择班级
    #     empty_label="-- 请选择班级 --"
    # )

    class Meta:
        model = User
        # 定义表单包含模型的哪些字段，移除class_in
        fields = ['username', 'wx_nickName', 'phone', 'gender', 'user_attribute']
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
        )
        # 删除班级处理逻辑
        # if self.cleaned_data.get('class_in'):
        #      user.class_in.add(self.cleaned_data.get('class_in'))
        
        return user

class ClassForm(forms.ModelForm):
    homeroom_teacher = forms.ModelChoiceField(
        queryset=User.objects.filter(user_attribute=2),
        label='班主任',
        required=False,
        empty_label="-- 请选择班主任 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 动态生成年份选项：当前年份前后5年
        current_year = datetime.datetime.now().year
        year_choices = [(f"{y}级", f"{y}级") for y in range(current_year - 5, current_year + 2)]
        self.fields['grade'].widget = forms.Select(
            choices=[('', '-- 请选择年级 --')] + year_choices,
            attrs={'class': 'form-select'}
        )

    class Meta:
        model = className
        fields = ['name', 'code', 'grade', 'homeroom_teacher', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入班级名称'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入班级编号（留空则自动生成）'}),
            # 'grade' widget is set in __init__
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '请输入班级描述'}),
        }
        help_texts = {
            'code': '班级编号必须唯一。如果不填写，系统将自动生成。',
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            # 检查唯一性，排除自身
            qs = className.objects.filter(code=code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("该班级编号已存在，请使用其他编号。")
        return code

class ClassTeacherForm(forms.ModelForm):
    teacher = forms.ModelChoiceField(
        queryset=User.objects.filter(user_attribute=2),
        label='选择教师',
        empty_label="-- 请选择教师 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = ClassTeacher
        fields = ['teacher', 'subject']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入教授科目'}),
        }

class AddStudentToClassForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(user_attribute=1), # 仅筛选学生
        label='选择学生',
        empty_label="-- 请选择学生 --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )