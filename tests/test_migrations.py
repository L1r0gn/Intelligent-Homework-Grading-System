# -*- coding: utf-8 -*-
"""
迁移健康度守护测试。

背景：`.gitignore` 里曾有一条 `*/migrations/`，把新生成的迁移文件全部挡在仓库之外。
后果是 BKTModule 长期没有迁移，本机能跑（表是手工建的），换台机器 `migrate`
不会报错，但根本不会创建那 5 张 bkt_* 表，页面运行时才 500。

注意：`makemigrations --check` **抓不到**这种情况 —— 没有 migrations 包的 app
不会进入迁移图，autodetector 直接跳过它。所以必须单独检查「有模型但没迁移」。
"""
import importlib

from django.apps import apps
from django.test import SimpleTestCase

# 本项目自己的 app（排除 django.contrib.* 与第三方）
LOCAL_APPS = {
    'userManageModule',
    'questionManageModule',
    'gradingModule',
    'assignmentAndClassModule',
    'BKTModule',
    'dkt_app',
}


class MigrationHygieneTest(SimpleTestCase):

    def test_apps_with_models_have_migrations_package(self):
        """有 ORM 模型的 app 必须存在 migrations 包。"""
        offenders = []
        for config in apps.get_app_configs():
            if config.name.split('.')[0] not in LOCAL_APPS:
                continue
            if not list(config.get_models()):
                continue  # dkt_app 只有 PyTorch 模型，没有 ORM 表，跳过
            try:
                importlib.import_module(f'{config.name}.migrations')
            except ImportError:
                offenders.append(config.label)

        self.assertEqual(
            offenders, [],
            f'以下 app 有模型但缺少 migrations 包，新环境 migrate 不会建表：{offenders}',
        )

    def test_no_pending_model_changes(self):
        """
        模型改动必须已经生成迁移文件。

        不用 `call_command('makemigrations', '--check')`：它会读 django_migrations 表，
        在 SimpleTestCase 里被禁止，也要求 CI 有数据库。
        这里直接用 autodetector 对比「磁盘上的迁移」与「当前模型」，全程不连库。
        """
        from django.db.migrations.autodetector import MigrationAutodetector
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.state import ProjectState

        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(loader.project_state(), ProjectState.from_apps(apps))
        changes = autodetector.changes(graph=loader.graph)

        pending = {
            app_label: [op.__class__.__name__ for migration in ops for op in migration.operations]
            for app_label, ops in changes.items()
            if app_label.split('.')[0] in LOCAL_APPS
        }

        self.assertEqual(
            pending, {},
            f'以下 app 的模型改动还没有生成迁移：{pending}；'
            '请执行 python manage.py makemigrations 并提交生成的文件',
        )
