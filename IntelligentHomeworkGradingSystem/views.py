from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import logging

from userManageModule.models import User
from questionManageModule.models import Problem
from gradingModule.models import Submission

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="app.log"
)
logger = logging.getLogger(__name__)

def helloWorld(request):
    return HttpResponse("Hello World!")

@login_required(login_url='login')
def dashboard(request):
    """
    系统首页仪表盘
    """
    context = {
        'user_count': User.objects.count(),
        'question_count': Problem.objects.count(),
        'submission_count': Submission.objects.count(),
        'recent_submissions': Submission.objects.order_by('-submitted_time')[:5]
    }
    return render(request, 'dashboard.html', context)
