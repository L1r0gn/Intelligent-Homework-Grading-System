from django.db import models

# Create your models here.
class students(models.Model):
    id = models.BigIntegerField(verbose_name="ID",primary_key=True) # 主键哈，用这个去find
    nickName = models.CharField(verbose_name="昵称",max_length="64") 
    phone = models.BigIntegerField(verbose_name="手机号",max_length="11") #后期考虑使用一下正则表达式验证




class teacher(models.Model):
    id = models.BigIntegerField(verbose_name="ID",primary_key=True) # 主键哈，用这个去find
    phone = models.BigIntegerField(verbose_name="手机号") #后期考虑使用一下正则表达式验证


class class_name(models.Model):
    id = models.BigIntegerField(verbose_name="班级",primary_key=True)
    name = models.CharField(verbose_name="班级名称")