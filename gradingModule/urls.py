from django.urls import path
from gradingModule import views

urlpatterns = [
    path('wx/submit/',views.submissionprocess),
    path('submissions/', views.submission_list, name='submission_list'),
    path('submissions/<int:submission_id>/', views.submission_detail, name='submission_detail'),
    path('submission/<int:submission_id>/regrade/', views.regrade_submission_view, name='regrade_submission'),
    path('submission-image/<int:submission_id>/', views.serve_submission_image, name='serve_submission_image'),
    path('wx/submissions/',views.showMySubmissions,name='showMySubmissions'),
    path('wx/submissions/<int:submission_id>/', views.getASubmission, name='get_a_submission'),
    path('submissions/batch-action/', views.submission_batch_action, name='submission_batch_action'),
    path('wx/submissions/assignment_id=<int:assignment_id>/', views.getSubmissionsByAssignmentId, name='get_submissions_by_assignment_id'),
]