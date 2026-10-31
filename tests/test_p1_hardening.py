# -*- coding: utf-8 -*-
"""
P1 加固相关的测试：

1. AI 批改的图片参数：公网地址走 URL，内网/本机必须转 base64
   （否则模型侧拉不到图，表现为"批改一直失败但没有报错"）
2. 题目存在性判断在非 Redis 后端下必须退化为直查数据库，不能误判
"""
import tempfile


from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from gradingModule.tasks import build_image_payload, is_publicly_reachable
from gradingModule.models import Submission
from questionManageModule import cache_utils
from questionManageModule.models import Problem, ProblemType, Subject
from userManageModule.models import User

PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
    b'\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
)


class PublicReachabilityTest(SimpleTestCase):
    """纯函数，不碰数据库。"""

    def test_loopback_is_not_public(self):
        for url in ('http://127.0.0.1:8000/x', 'http://localhost:8000/x',
                    'http://0.0.0.0:8000/x'):
            self.assertFalse(is_publicly_reachable(url), url)

    def test_private_networks_are_not_public(self):
        for url in ('http://192.168.1.5/x', 'http://10.0.0.7/x', 'http://172.16.3.4/x'):
            self.assertFalse(is_publicly_reachable(url), url)

    def test_public_hosts_are_reachable(self):
        for url in ('https://example.com/x', 'http://8.8.8.8/x'):
            self.assertTrue(is_publicly_reachable(url), url)

    def test_local_domain_is_not_public(self):
        self.assertFalse(is_publicly_reachable('http://myhost.local/x'))


class ImagePayloadTest(TestCase):
    """内网部署时，图片必须以 base64 内联，不能只给一个模型拉不到的 URL。"""

    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_dir)
        self.override.enable()

        self.user = User.objects.create_user(username='p1_student', password='pwd')
        self.subject = Subject.objects.create(name='物理', code='PHY_P1')
        ptype = ProblemType.objects.create(name='解答题', code='ESSAY_P1')
        self.problem = Problem.objects.create(
            title='求加速度', problem_type=ptype, subject=self.subject, points=10,
        )
        self.submission = Submission.objects.create(
            problem=self.problem, student=self.user, status='PENDING',
            submitted_time=timezone.now(),
            submitted_image=SimpleUploadedFile('answer.png', PNG_BYTES, content_type='image/png'),
        )

    def tearDown(self):
        self.override.disable()

    @override_settings(SERVER_BASE_URL='http://127.0.0.1:8000')
    def test_local_host_falls_back_to_base64(self):
        payload = build_image_payload(self.submission)
        self.assertIsNotNone(payload)
        self.assertTrue(payload.startswith('data:image/png;base64,'), payload[:40])

    @override_settings(SERVER_BASE_URL='https://grading.example.com')
    def test_public_host_uses_url(self):
        payload = build_image_payload(self.submission)
        self.assertEqual(
            payload,
            f'https://grading.example.com/api/v1/submissions/{self.submission.id}/image/',
        )

    @override_settings(SERVER_BASE_URL='http://127.0.0.1:8000')
    def test_returns_none_when_file_missing(self):
        """本地文件丢失时返回 None，调用方据此标记 RUNTIME_ERROR，而不是抛异常。"""
        self.submission.submitted_image.delete(save=False)
        self.assertIsNone(build_image_payload(self.submission))


class QuestionIndexFallbackTest(TestCase):
    """缓存后端不是 Redis 时，题存在性判断必须退化直查库，不能误判成不存在。"""

    def setUp(self):
        self.subject = Subject.objects.create(name='化学', code='CHEM_P1')
        ptype = ProblemType.objects.create(name='选择', code='CHOICE_P1')
        self.problem = Problem.objects.create(
            title='1+1', problem_type=ptype, subject=self.subject, points=5, is_active=True,
        )

    def test_fallback_queries_database(self):
        locmem = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
        with override_settings(CACHES=locmem):
            cache_utils._redis_client = None
            try:
                self.assertTrue(cache_utils.question_may_exist(self.problem.id))
                self.assertFalse(cache_utils.question_may_exist(99_999_999))
            finally:
                cache_utils._redis_client = None

    def test_inactive_problem_not_reported(self):
        locmem = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
        self.problem.is_active = False
        self.problem.save(update_fields=['is_active'])
        with override_settings(CACHES=locmem):
            cache_utils._redis_client = None
            try:
                self.assertFalse(cache_utils.question_may_exist(self.problem.id))
            finally:
                cache_utils._redis_client = None


class QuestionDetailContractTest(TestCase):
    """
    题目详情接口的契约：不返回内部字段、不改动缓存内容。

    说明：Django 的缓存后端（Redis / LocMem）读写时都会序列化，返回的是副本，
    所以旧写法 data.pop() 并不会真的污染缓存 —— 本测试不会因为回退而失败。
    保留它是为了防止将来换成不序列化的自定义后端时踩坑，
    同时锁住"subject_id 不外泄"这个对外接口约定。
    """

    def setUp(self):
        from questionManageModule.models import ProblemContent
        self.user = User.objects.create_user(username='cache_student', password='pwd')
        self.user.user_attribute = 1
        self.user.save()
        self.subject = Subject.objects.create(name='生物', code='BIO_P1')
        self.user.authorized_subjects.add(self.subject)
        ptype = ProblemType.objects.create(name='填空', code='BLANK_P1')
        content = ProblemContent.objects.create(content='细胞壁的主要成分是？')
        self.problem = Problem.objects.create(
            title='细胞壁', problem_type=ptype, subject=self.subject,
            content=content, points=5, is_active=True,
        )

    def test_response_hides_internal_field_and_keeps_cache_intact(self):
        from django.core.cache import cache
        from rest_framework_simplejwt.tokens import RefreshToken

        locmem = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
        with override_settings(CACHES=locmem):
            cache.clear()
            cache_utils._redis_client = None
            try:
                auth = {'HTTP_AUTHORIZATION': f'Bearer {RefreshToken.for_user(self.user).access_token}'}
                url = f'/api/v1/questions/{self.problem.id}/'

                first = self.client.get(url, **auth)
                self.assertEqual(first.status_code, 200)
                self.assertNotIn('subject_id', first.json()['question'], '内部字段不应返回前端')

                cached = cache.get(f'question:detail:{self.problem.id}')
                self.assertIn('subject_id', cached, '缓存内容被接口污染了')

                second = self.client.get(url, **auth)
                self.assertEqual(second.status_code, 200)
            finally:
                cache_utils._redis_client = None
