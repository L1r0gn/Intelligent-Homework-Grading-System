# -*- coding: utf-8 -*-
"""
接口越权防护测试。

覆盖三个真实存在的越权缺陷（修复前均可复现）：
1. 提交接口信任请求体里的 userId —— 学生可以他人身份提交
2. 提交详情接口不校验归属 —— 任意登录用户可读他人成绩与作答图片
3. 作业提交列表接口没有认证 —— 匿名即可拉取全班提交
"""
import json
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from assignmentAndClassModule.models import Assignment, AssignmentStatus
from gradingModule.models import Submission
from questionManageModule.models import Problem, ProblemType, Subject
from userManageModule.models import User, className


class AuthorizationTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(username='t_auth', password='pwd')
        cls.teacher.user_attribute = 2
        cls.teacher.save()

        cls.student_a = User.objects.create_user(username='s_a', password='pwd')
        cls.student_a.user_attribute = 1
        cls.student_a.save()

        cls.student_b = User.objects.create_user(username='s_b', password='pwd')
        cls.student_b.user_attribute = 1
        cls.student_b.save()

        cls.subject = Subject.objects.create(name='数学', code='MATH_AUTH')
        cls.problem_type = ProblemType.objects.create(name='选择题', code='CHOICE_AUTH')
        cls.problem = Problem.objects.create(
            title='1+1=?', problem_type=cls.problem_type, subject=cls.subject,
            points=10, is_active=True,
        )

        cls.submission_a = Submission.objects.create(
            problem=cls.problem, student=cls.student_a,
            submitted_text='A', choose_answer='A', status='GRADED', score=10,
            submitted_time=timezone.now(),
        )

        cls.klass = className.objects.create(name='测试班', created_by=cls.teacher)
        cls.assignment = Assignment.objects.create(
            problem=cls.problem, title='作业一', teacher=cls.teacher, target_class=cls.klass,
        )
        cls.status = AssignmentStatus.objects.create(
            assignment=cls.assignment, submission=cls.submission_a,
            student=cls.student_a, submitted_at=timezone.now(),
        )

    def auth(self, user):
        token = RefreshToken.for_user(user).access_token
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


class SubmissionDetailAuthorizationTest(AuthorizationTestBase):

    def test_student_cannot_read_others_submission(self):
        """学生 B 读学生 A 的提交 → 403"""
        r = self.client.get(f'/api/v1/submissions/{self.submission_a.id}/', **self.auth(self.student_b))
        self.assertEqual(r.status_code, 403)

    def test_student_can_read_own_submission(self):
        r = self.client.get(f'/api/v1/submissions/{self.submission_a.id}/', **self.auth(self.student_a))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['score'], 10)

    def test_teacher_can_read_any_submission(self):
        r = self.client.get(f'/api/v1/submissions/{self.submission_a.id}/', **self.auth(self.teacher))
        self.assertEqual(r.status_code, 200)

    def test_anonymous_cannot_read_submission(self):
        r = self.client.get(f'/api/v1/submissions/{self.submission_a.id}/')
        self.assertEqual(r.status_code, 401)


class AssignmentSubmissionsAuthorizationTest(AuthorizationTestBase):

    def url(self):
        return f'/api/v1/assignments/{self.assignment.id}/submissions/'

    def test_anonymous_cannot_list(self):
        """未登录即可拉全班提交 —— 修复前正是如此"""
        self.assertEqual(self.client.get(self.url()).status_code, 401)

    def test_student_cannot_list(self):
        self.assertEqual(self.client.get(self.url(), **self.auth(self.student_a)).status_code, 403)

    def test_teacher_can_list(self):
        self.assertEqual(self.client.get(self.url(), **self.auth(self.teacher)).status_code, 200)


class SubmissionIdentityTest(AuthorizationTestBase):

    def test_submit_ignores_spoofed_user_id(self):
        """学生 B 在请求体里传学生 A 的 userId，提交记录仍应归属 B"""
        payload = {
            'questionId': self.problem.id,
            'selectedAnswer': 'B',
            'from': 'question',
            'userId': self.student_a.id,  # 伪造
        }
        with patch('gradingModule.views.process_and_grade_submission.delay'):
            r = self.client.post('/api/v1/submissions/', data=json.dumps(payload),
                                 content_type='application/json', **self.auth(self.student_b))

        self.assertEqual(r.status_code, 200)
        new_sub = Submission.objects.get(id=r.json()['id'])
        self.assertEqual(new_sub.student_id, self.student_b.id,
                         '提交记录被记到了伪造的 userId 名下')
        self.assertNotEqual(new_sub.student_id, self.student_a.id)
