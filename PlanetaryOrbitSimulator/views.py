from django.shortcuts import render
import matplotlib.pyplot as plt

from PlanetaryOrbitSimulator.models import SimulationImage
from PlanetaryOrbitSimulator.twobodytesting import TwoBodyTesting
storage = [0,[],[]]

def testingPage(request):
    context = {}
    return render(request, "TestingPage.html", context)

def homePage(request):
    context = {}
    plt.close('all')
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
    simulationTime = storage[0]
    listOfBodies = storage[1]
    bodyPoints = storage[2]
    setTicks = (86400*5)/60 + simulationTime


    twoBodySim = TwoBodyTesting()
    simulationTime, listOfBodies, bodyPoints = twoBodySim.runSimulation(setTicks, simulationTime, listOfBodies, bodyPoints, False)

    storage[0] = simulationTime
    storage[1] = listOfBodies
    storage[2] = bodyPoints

    context = {}

    return render(request, "runSimulationPage.html", context)