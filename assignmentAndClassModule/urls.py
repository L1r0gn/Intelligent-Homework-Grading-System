from assignmentAndClassModule.views import problem_meta_data
from django.urls import path
import assignmentAndClassModule.views

urlpatterns = [
    path('wx/get_problem_meta_data/' , assignmentAndClassModule.views.problem_meta_data,name='get_problem_meta_data'),
    path('wx/push_assignment/' , assignmentAndClassModule.views.push_assignment,name='push_assignment'),
    path('wx/show_assignment/', assignmentAndClassModule.views.student_assignments, name='student_assignments'),
    path('wx/get_student_homework_detail/<int:assignment_id>/',assignmentAndClassModule.views.get_student_homework_detail,name='get_student_homework_detail'),
    path('wx/teacher_get_assignments/<int:class_id>',assignmentAndClassModule.views.teacher_get_assignments,name='teacher_get_assignments'),
    path('wx/homeworkGradingProcess/<int:assignment_id>/',assignmentAndClassModule.views.homeworkGradingProcess,name='homeworkGradingProcess'),
    path('wx/teacher_get_assignments_detail/<int:class_id>/<int:assignment_id>/',assignmentAndClassModule.views.teacher_get_assignments_detail,name='teacher_get_assignments_detail'),
    path('wx/teacher_get_students_assignments_list/<int:class_id>/<int:assignment_id>/',assignmentAndClassModule.views.teacher_get_students_assignments_list,name='teacher_get_students_assignments_list'),
]