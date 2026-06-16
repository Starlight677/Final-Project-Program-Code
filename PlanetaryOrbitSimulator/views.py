import threading
from idlelib.rpc import request_queue

from django.http import HttpResponse
from django.shortcuts import render

from twobodytesting import TwoBodyTesting
stopEvent = threading.Event() # See if this works

def testingPage(request):
    context = {}
    return render(request, "TestingPage.html", context)

def homePage(request):
    context = {}
    return render(request, "HomePage.html", context)

def settingsPage(request):
    context = {}
    return render(request, "SettingsPage.html", context)

def createPage(request):
    context = {}
    return render(request, "NewSystemPage.html", context)

def loadingPage(request):
    context = {}
    return render(request, "LoadSystemPage.html", context)

def runSimulation(request):
    context = {}
    return render(request, "runSimulationPage.html", context)