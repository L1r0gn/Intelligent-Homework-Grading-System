from django.db import models


class class_name(models.Model):
    name = models.CharField(verbose_name="班级名称", max_length=30)

    # 便于在下拉框中显示班级名称
    def __str__(self):
        return self.name


class User(models.Model):
    genders_choices = [
        (1, '男'),
        (2, '女'),
    ]
    user_attribute_choices = [
        (1, 'student'),
        (2, 'teacher'),
    ]
    nickName = models.CharField(verbose_name="昵称", max_length=30)
    phone = models.BigIntegerField(verbose_name="手机号")
    gender = models.SmallIntegerField(verbose_name="性别", choices=genders_choices)
    user_attribute = models.SmallIntegerField(verbose_name="属性", choices=user_attribute_choices)
    # 外键关联班级表，允许为空（如果用户可以不关联班级）
    class_in = models.ForeignKey(
        to="class_name",
        to_field="id",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="所属班级"
    )