from django.http import HttpResponse
from django.shortcuts import render
import logging


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="app.log"
)
logger = logging.getLogger(__name__)
def helloWorld(request):
    return HttpResponse("Hello World!")