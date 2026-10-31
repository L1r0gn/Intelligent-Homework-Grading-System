"""把 Submission.status 归一为「批改流程状态」的单一枚举。

历史问题：同一字段被写入过 PENDING / GRADING / SUBMITTED / GRADED /
ACCEPTED / WRONG_ANSWER / COMPILE_ERROR / RUNTIME_ERROR 八种取值，
其中 ACCEPTED / WRONG_ANSWER 表达的是「答案对错」而不是「批改进度」，
导致 is_correct 判定、后台筛选、模板配色三处口径互相矛盾。

本迁移只做数据归一，不改字段类型：
    SUBMITTED    -> PENDING   （语义等同：已提交、等批改）
    ACCEPTED     -> GRADED    （并补齐 score = 题目满分）
    WRONG_ANSWER -> GRADED    （并补齐 score = 0）
其余取值保持不变。
"""

from django.db import migrations, models

BATCH_SIZE = 500


def forwards(apps, schema_editor):
    Submission = apps.get_model('gradingModule', 'Submission')

    # SUBMITTED 与 PENDING 语义重复，直接合并
    Submission.objects.filter(status='SUBMITTED').update(status='PENDING')

    # ACCEPTED / WRONG_ANSWER 拆成「已批改 + 分数」，对错改由分数派生
    legacy_qs = Submission.objects.filter(
        status__in=['ACCEPTED', 'WRONG_ANSWER']
    ).select_related('problem')

    for submission in legacy_qs.iterator(chunk_size=BATCH_SIZE):
        if submission.status == 'ACCEPTED':
            if submission.score is None:
                points = getattr(submission.problem, 'points', None)
                submission.score = points if points is not None else 0
        else:  # WRONG_ANSWER
            if submission.score is None:
                submission.score = 0
        submission.status = 'GRADED'
        submission.save(update_fields=['status', 'score'])


def backwards(apps, schema_editor):
    """无法无损回滚（对错信息已折叠进分数），保留空实现。"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gradingModule', '0003_alter_submission_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', '待批改'),
                    ('GRADING', '批改中'),
                    ('GRADED', '已批改'),
                    ('COMPILE_ERROR', '编译错误'),
                    ('RUNTIME_ERROR', '运行错误'),
                ],
                default='PENDING',
                help_text='仅表示批改流程进度；答案对错请使用 is_correct',
                max_length=20,
                verbose_name='批改状态',
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
