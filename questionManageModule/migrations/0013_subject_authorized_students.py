from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userManageModule', '0001_initial'),
        ('questionManageModule', '0012_studentmastery'),
    ]

    operations = [
        migrations.AddField(
            model_name='subject',
            name='authorized_students',
            field=models.ManyToManyField(
                blank=True,
                related_name='authorized_subjects',
                to='userManageModule.User',
                verbose_name='授权学生'
            ),
        ),
    ]
