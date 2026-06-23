from django.shortcuts import render
import matplotlib.pyplot as plt

from PlanetaryOrbitSimulator.twobodytesting import PlanetarySimulationEngine

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

def runSimulation(request, restartSimulation = 0, autoRunSimulation = 0):

    try: # Load variables from session if they exist, otherwise set to starting values
        simulationTime = request.session["simulationTime"]
        listOfBodies = request.session["listOfBodies"]
        bodyPoints = request.session["bodyPoints"]
        secondsPerSimulationTick = request.session["secondsPerSimulationTick"]
        setTicks = (86400*5)/secondsPerSimulationTick + simulationTime
    except:
        restartSimulation = 1

    if restartSimulation == 1:
        simulationTime = 0
        listOfBodies = []
        bodyPoints = []
        secondsPerSimulationTick = 60
        request.session["secondsPerSimulationTick"] = secondsPerSimulationTick
        setTicks = (86400*5)/secondsPerSimulationTick


    simulationEngine = PlanetarySimulationEngine() # Run simulation for specified time interval
    simulationTime, listOfBodies, bodyPoints, simulationSize = simulationEngine.runSimulation(setTicks, simulationTime, listOfBodies, bodyPoints, secondsPerSimulationTick)

    # Update stored variables
    request.session["simulationTime"] = simulationTime
    request.session["listOfBodies"] = listOfBodies
    request.session["bodyPoints"] = bodyPoints

    daysElapsed = round((simulationTime/86400)*secondsPerSimulationTick) # Simulation time in days
    statedSimulationSize = round(simulationSize/1000) # Simulation size in kilometers
    fStatedSimulationSize = f"{statedSimulationSize:,}" #Adds commas to the number
    context = {"simulationSize": fStatedSimulationSize, "daysElapsed": daysElapsed, "autoRunSimulation": autoRunSimulation}

    return render(request, "runSimulationPage.html", context)