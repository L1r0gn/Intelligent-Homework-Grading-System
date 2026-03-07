from django.core.management.base import BaseCommand
from userManageModule.models import User
from questionManageModule.models import KnowledgePoint, Problem
from gradingModule.models import Submission
import datetime
import random

class Command(BaseCommand):
    help = 'Creates test data for DKT model training and prediction.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating test data...'))

        # 1. Create a test student
        student, created = User.objects.get_or_create(
            username='dkt_test_student',
            defaults={'user_attribute': 1, 'password': 'testpassword123', 'phone': 12345678901}
        )
        if created:
            student.set_password('testpassword123')
            student.save()
            self.stdout.write(self.style.SUCCESS(f'Created test student: {student.username} (ID: {student.id})'))
        else:
            self.stdout.write(self.style.WARNING(f'Test student {student.username} (ID: {student.id}) already exists.'))

        # 2. Create some knowledge points
        kp_names = ['概念A', '概念B', '概念C', '概念D', '概念E']
        knowledge_points = []
        for name in kp_names:
            kp, created = KnowledgePoint.objects.get_or_create(name=name)
            knowledge_points.append(kp)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created knowledge point: {kp.name} (ID: {kp.id})'))
            else:
                self.stdout.write(self.style.WARNING(f'Knowledge point {kp.name} (ID: {kp.id}) already exists.'))

        # 3. Create some problems and link them to knowledge points
        problems = []
        problem_data = [
            ('问题1', [knowledge_points[0]]),
            ('问题2', [knowledge_points[0], knowledge_points[1]]),
            ('问题3', [knowledge_points[1]]),
            ('问题4', [knowledge_points[2]]),
            ('问题5', [knowledge_points[0], knowledge_points[2]]),
            ('问题6', [knowledge_points[3]]),
            ('问题7', [knowledge_points[1], knowledge_points[3]]),
            ('问题8', [knowledge_points[4]]),
        ]

        for name, kps_for_problem in problem_data:
            problem, created = Problem.objects.get_or_create(
                title=name,
                defaults={'description': f'{name}的描述', 'difficulty': random.randint(1, 5)}
            )
            if created:
                problem.knowledge_points.set(kps_for_problem)
                problems.append(problem)
                self.stdout.write(self.style.SUCCESS(f'Created problem: {problem.title} (ID: {problem.id})'))
            else:
                self.stdout.write(self.style.WARNING(f'Problem {problem.title} (ID: {problem.id}) already exists.'))
                problems.append(problem) # Ensure problem is added even if not created

        # 4. Create submissions for the test student
        # Simulate a sequence of submissions
        submission_data = [
            (problems[0], 0.5), # Problem 1, Score 0.5
            (problems[1], 1.0), # Problem 2, Score 1.0
            (problems[2], 0.0), # Problem 3, Score 0.0
            (problems[0], 1.0), # Problem 1 again, Score 1.0
            (problems[3], 0.8), # Problem 4, Score 0.8
            (problems[1], 0.2), # Problem 2 again, Score 0.2
            (problems[4], 0.9), # Problem 5, Score 0.9
            (problems[5], 0.1), # Problem 6, Score 0.1
            (problems[6], 1.0), # Problem 7, Score 1.0
            (problems[7], 0.7), # Problem 8, Score 0.7
        ]

        base_time = datetime.datetime.now(datetime.timezone.utc)
        for i, (problem, score) in enumerate(submission_data):
            # Ensure each submission has a slightly different timestamp for ordering
            submitted_time = base_time + datetime.timedelta(minutes=i)
            Submission.objects.create(
                student=student,
                problem=problem,
                score=score,
                submitted_time=submitted_time
            )
            self.stdout.write(self.style.SUCCESS(f'Created submission for {student.username} on {problem.title} with score {score}'))
        
        self.stdout.write(self.style.SUCCESS(f'Test data created successfully for student ID: {student.id}'))
