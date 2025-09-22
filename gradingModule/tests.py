from gradingModule.models import Submission

# Create your tests here.
submissions = Submission.objects.all()
print(submissions)