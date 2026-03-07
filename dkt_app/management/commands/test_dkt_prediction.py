from django.core.management.base import BaseCommand
from userManageModule.models import User
from django.test import RequestFactory
from dkt_app.views import get_student_mastery_view
import json
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Tests the DKT prediction API endpoint for the dkt_test_student.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing DKT prediction API...'))

        try:
            # 1. Get the ID of the dkt_test_student
            student = User.objects.get(username='dkt_test_student')
            student_id = student.id
            self.stdout.write(self.style.SUCCESS(f'Found dkt_test_student with ID: {student_id}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('dkt_test_student not found. Please run `python manage.py create_test_data` first.'))
            return

        # 2. Simulate a request to the API endpoint
        factory = RequestFactory()
        request = factory.get(f'/dkt/mastery/{student_id}/')

        # 3. Call the view function directly
        response = get_student_mastery_view(request, student_id)

        # 4. Process the response
        if response.status_code == 200:
            data = json.loads(response.content)
            self.stdout.write(self.style.SUCCESS('DKT prediction API call successful!'))
            
            # 验证所有必需字段
            required_fields = [
                'student_id', 'student_name', 'mastery_predictions', 
                'exercise_sequence', 'concept_labels', 'avg_mastery_history',
                'last_concept_mastery', 'current_avg_mastery', 'exercise_times'
            ]
            
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self.stdout.write(self.style.ERROR(f'Missing required fields: {missing_fields}'))
            else:
                self.stdout.write(self.style.SUCCESS('All required fields present!'))
                
            # 显示关键数据摘要
            self.stdout.write(self.style.HTTP_INFO(f'Student: {data["student_name"]} (ID: {data["student_id"]})'))
            self.stdout.write(self.style.HTTP_INFO(f'Exercise count: {len(data["exercise_sequence"])}'))
            self.stdout.write(self.style.HTTP_INFO(f'Concept count: {len(data["concept_labels"])}'))
            self.stdout.write(self.style.HTTP_INFO(f'Current avg mastery: {data["current_avg_mastery"]:.2%}'))
            
            if data.get('last_concept_mastery'):
                self.stdout.write(self.style.SUCCESS('Last concept mastery data found:'))
                for concept, mastery in list(data['last_concept_mastery'].items())[:3]:
                    self.stdout.write(f'  - {concept}: {mastery:.2%}')
            
            # Basic validation: Check if predictions exist
            if data.get('mastery_predictions') and data.get('exercise_sequence'):
                self.stdout.write(self.style.SUCCESS('Mastery predictions and exercise sequence found in response.'))
                self.stdout.write(self.style.SUCCESS('DKT prediction functionality seems to be working correctly.'))
            else:
                self.stdout.write(self.style.WARNING('No mastery predictions or exercise sequence found in response. Check data or model.'))
        else:
            self.stdout.write(self.style.ERROR(f'DKT prediction API call failed with status code {response.status_code}.'))
            self.stdout.write(self.style.ERROR(response.content.decode('utf-8')))
