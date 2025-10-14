from django.contrib.auth.models import AbstractUser
from django.db import models

class className(models.Model):
    name = models.CharField(verbose_name="班级名称", max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_classes'
    )
    def __str__(self):
        return self.name

class User(AbstractUser):
    genders_choices = [
        (1, '男'),
        (2, '女'),
    ]
    phone = models.BigIntegerField(verbose_name="手机号",null=True,blank=True,default=13500000000)
    gender = models.SmallIntegerField(verbose_name="性别", choices=genders_choices,null=True,blank=True)
    user_attribute = models.SmallIntegerField(verbose_name="属性", choices=[
            (0,'未定义'),
            (1, '学生'),
            (2, '老师'),
            (3, '管理员'),
            (4, '超级管理员'),
        ],default=0)
    # password = models.CharField(verbose_name="密码", max_length=128,default='12345678')
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
        to="className",
        to_field="id",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="所属班级"
    )