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

def createPage(request, templateIndex = 0):
    request.session["templateIndex"] = templateIndex
    templatesList = ["Inner Solar System", "Moons of Jupiter"]
    context = {"templatesList": templatesList, "templateIndex": templateIndex}
    return render(request, "NewSystemPage.html", context)

def loadingPage(request):
    try:
        templateIndex = request.session["templateIndex"]
    except:
        request.session["templateIndex"] = 0
    context = {}
    return render(request, "LoadSystemPage.html", context)

def runSimulation(request, restartSimulation = 0, autoRunSimulation = 0):
    simulationEngine = PlanetarySimulationEngine()
    try: # Load variables from session if they exist, otherwise set to starting values
        simulationTime = request.session["simulationTime"]
        listOfBodies = request.session["listOfBodies"]
        bodyPoints = request.session["bodyPoints"]
        secondsPerSimulationTick = request.session["secondsPerSimulationTick"]
        simulationSize = request.session["simulationSize"]
        ticksPerStorageUpdate = request.session["ticksPerStorageUpdate"]
        ticksPerPageUpdate = request.session["ticksPerPageUpdate"]
        setTicks = ticksPerPageUpdate + simulationTime
    except:
        # If variables not found, start new session
        restartSimulation = 1

    if restartSimulation == 1:
        # Load and initialise new simulation setup from template
        listOfBodies, simulationSize, ticksPerStorageUpdate, ticksPerPageUpdate, secondsPerSimulationTick, bodyPoints \
            = simulationEngine.loadTemplates(request.session["templateIndex"])
        simulationTime = 0
        setTicks = 0
        # Set fixed values
        request.session["simulationSize"] = simulationSize
        request.session["ticksPerStorageUpdate"] = ticksPerStorageUpdate
        request.session["ticksPerPageUpdate"] = ticksPerPageUpdate
        request.session["secondsPerSimulationTick"] = secondsPerSimulationTick

    # Run instance of the simulation
    simulationTime, listOfBodies, bodyPoints, simulationSize = simulationEngine.runSimulation(setTicks, simulationTime, listOfBodies, bodyPoints, secondsPerSimulationTick, simulationSize, ticksPerStorageUpdate)

    # Update stored variables
    request.session["simulationTime"] = simulationTime
    request.session["listOfBodies"] = listOfBodies
    request.session["bodyPoints"] = bodyPoints

    daysElapsed = round((simulationTime/86400)*secondsPerSimulationTick, 2) # Simulation time in days
    daysPerTick = round((ticksPerPageUpdate/86400)*secondsPerSimulationTick, 2)
    statedSimulationSize = round(simulationSize/500) # Simulation diameter in kilometers
    fStatedSimulationSize = f"{statedSimulationSize:,}" #Adds commas to the number
    AUStatedSimulationSize = round(statedSimulationSize/1.495979e8,3) # Calculates simulation diameter in Astronomical Units to 3DP

    context = {"simulationSizeKM": fStatedSimulationSize, "simulationSizeAU": AUStatedSimulationSize,
               "daysElapsed": daysElapsed, "daysPerTick": daysPerTick, "autoRunSimulation": autoRunSimulation}

    return render(request, "runSimulationPage.html", context)