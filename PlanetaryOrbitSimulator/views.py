from django.shortcuts import render
import matplotlib.pyplot as plt

from PlanetaryOrbitSimulator.models import SimulationImage
from PlanetaryOrbitSimulator.twobodytesting import TwoBodyTesting

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

    try: # Load variables from session if they exist, otherwise set to starting values
        simulationTime = request.session["simulationTime"]
        listOfBodies = request.session["listOfBodies"]
        bodyPoints = request.session["bodyPoints"]
        setTicks = (86400*5)/60 + simulationTime
    except:
        simulationTime = 0
        listOfBodies = []
        bodyPoints = []
        setTicks = (86400*5)/60


    twoBodySim = TwoBodyTesting() # Run simulation for specified time interval
    simulationTime, listOfBodies, bodyPoints = twoBodySim.runSimulation(setTicks, simulationTime, listOfBodies, bodyPoints, False)

    # Update stored variables
    request.session["simulationTime"] = simulationTime
    request.session["listOfBodies"] = listOfBodies
    request.session["bodyPoints"] = bodyPoints

    context = {}

    return render(request, "runSimulationPage.html", context)