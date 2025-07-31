from cgi import maxlen

from django.contrib.auth.models import AbstractUser
from django.db import models

class class_name(models.Model):
    name = models.CharField(verbose_name="班级名称", max_length=30)
    def __str__(self):
        return self.name

class User(AbstractUser):
    genders_choices = [
        (1, '男'),
        (2, '女'),
    ]
    user_attribute_choices = [
        (1, 'student'),
        (2, 'teacher'),
    ]
    # nickName = models.CharField(verbose_name="昵称", max_length=30)
    phone = models.BigIntegerField(verbose_name="手机号",null=True,blank=True)
    gender = models.SmallIntegerField(verbose_name="性别", choices=genders_choices,null=True,blank=True)
    user_attribute = models.SmallIntegerField(verbose_name="属性", choices=user_attribute_choices,null=True,blank=True)

    #微信字段
    openid = models.CharField(max_length=64,unique=True,null=True,blank=True, verbose_name="微信OpenID")
    unionid = models.CharField(max_length=64,null=True,blank=True,verbose_name="微信UnionID")
    wx_nickName = models.CharField(max_length=128,null=True,blank=True,verbose_name='微信昵称')
    wx_avatar = models.URLField(null=True,blank=True,verbose_name='微信头像')
    # 其他微信相关信息
    session_key = models.CharField(max_length=128, null=True, blank=True, verbose_name="微信会话密钥")
    wx_country = models.CharField(max_length=30, null=True, blank=True, verbose_name="国家")
    wx_province = models.CharField(max_length=30, null=True, blank=True, verbose_name="省份")
    wx_city = models.CharField(max_length=30, null=True, blank=True, verbose_name="城市")

    # 最后登录时间（自动更新）
    last_login_time = models.DateTimeField(auto_now=True, verbose_name="最后登录时间")

    # 外键关联班级表，允许为空（如果用户可以不关联班级）
    class_in = models.ForeignKey(
        to="class_name",
        to_field="id",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="所属班级"
    )