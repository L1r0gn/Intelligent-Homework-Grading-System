from django.contrib import admin
from django.urls import path
from gradingModule import views

urlpatterns = [
    path('submit/',views.submissionprocess),
]


