from idlelib.rpc import request_queue

from django.http import HttpResponse
from django.shortcuts import render


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