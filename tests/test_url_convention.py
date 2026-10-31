# -*- coding: utf-8 -*-
"""
路由命名规范守护测试。

规则来源：docs/URL_SPEC.md
1. 路径参数一律 /<int:xxx>/，禁止 key=value；
2. 结尾必须带斜杠；
3. 路由名 snake_case；
4. 全限定名不得重复；
5. 业务路由必须落在页面命名空间或 api/v1 下。

这些断言存在的意义：防止 URL 再次退化成 `assignment_id=5` 这种写法。
"""
import re

from django.test import SimpleTestCase
from django.urls import URLResolver, get_resolver

# Django Admin 自动生成的路由不适用本规范，整体跳过
SKIP_NAMESPACES = {'admin'}

# Django 内置的媒体路由（static() 注入）不以斜杠结尾
ALLOW_PATTERN_PREFIXES = ('^media/',)


def _iter_patterns(patterns, namespace=None, prefix=''):
    """递归遍历 URLConf，产出 (全限定名, 完整路径, 是否在跳过命名空间内)。"""
    for entry in patterns:
        if isinstance(entry, URLResolver):
            child_ns = entry.namespace or namespace
            yield from _iter_patterns(entry.url_patterns, child_ns, prefix + str(entry.pattern))
        else:
            full = f'{namespace}:{entry.name}' if namespace and entry.name else entry.name
            skipped = namespace in SKIP_NAMESPACES
            yield full, prefix + str(entry.pattern), skipped


class URLConventionTest(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.routes = [
            (name, pattern)
            for name, pattern, skipped in _iter_patterns(get_resolver().url_patterns)
            if not skipped
        ]

    def test_no_key_value_path_params(self):
        """路径参数不允许写成 key=value。"""
        offenders = [p for _, p in self.routes if re.search(r'\w+=<', p)]
        self.assertEqual(offenders, [], f'发现 key=value 形式的路径参数：{offenders}')

    def test_trailing_slash(self):
        """所有路由必须以斜杠结尾（media 静态路由除外）。"""
        offenders = [
            p for _, p in self.routes
            if p and not p.endswith('/') and not p.startswith(ALLOW_PATTERN_PREFIXES)
        ]
        self.assertEqual(offenders, [], f'发现缺少结尾斜杠的路由：{offenders}')

    def test_route_names_snake_case(self):
        """路由名只允许小写字母、数字、下划线和命名空间冒号。"""
        offenders = [
            n for n, _ in self.routes
            if n and not re.fullmatch(r'[a-z0-9_]+(:[a-z0-9_]+)?', n)
        ]
        self.assertEqual(offenders, [], f'发现不符合 snake_case 的路由名：{offenders}')

    def test_no_duplicate_names(self):
        """全限定路由名必须唯一，否则 reverse 会命中错的那条。"""
        seen, dups = {}, []
        for name, pattern in self.routes:
            if not name:
                continue
            if name in seen:
                dups.append((name, seen[name], pattern))
            seen[name] = pattern
        self.assertEqual(dups, [], f'发现重复的路由名：(名称, 首次路径, 重复路径) {dups}')

    def test_no_duplicate_paths(self):
        """完整路径不得重复注册。"""
        seen, dups = {}, []
        for name, pattern in self.routes:
            if not pattern:
                continue
            if pattern in seen:
                dups.append((pattern, seen[pattern], name))
            seen[pattern] = name
        self.assertEqual(dups, [], f'发现重复注册的路径：(路径, 首个名称, 重复名称) {dups}')

    def test_api_namespace_isolated(self):
        """/api/v1/ 下只允许 JSON 接口，命名空间必须以 _api 结尾。"""
        offenders = []
        for name, pattern in self.routes:
            if not pattern.startswith('api/v1/'):
                continue
            namespace = (name or '').split(':')[0] if ':' in (name or '') else ''
            if not namespace.endswith('_api'):
                offenders.append((name, pattern))
        self.assertEqual(offenders, [], f'API 命名空间下出现了非接口路由：{offenders}')
