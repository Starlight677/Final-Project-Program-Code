from django.shortcuts import render
import matplotlib.pyplot as plt
from.models import StoredSimulation

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
    templatesList = ["Inner Solar System", "Galilean Moons of Jupiter", "Ascendia A Star"]
    context = {"templatesList": templatesList, "templateIndex": templateIndex}
    return render(request, "NewSystemPage.html", context)

def loadingPage(request):
    try: # Test if index can be loaded - if not, set it to default
        templateIndex = request.session["templateIndex"]
    except:
        request.session["templateIndex"] = 0
    context = {}
    return render(request, "LoadSystemPage.html", context)

def loadValues(objectToLoad, objectLoadFrom):
    # Copy simulation values to or from database
    objectToLoad.simulationTime = objectLoadFrom.simulationTime
    objectToLoad.simulationSize = objectLoadFrom.simulationSize
    objectToLoad.listOfBodies = objectLoadFrom.listOfBodies
    objectToLoad.bodyPoints = objectLoadFrom.bodyPoints
    objectToLoad.ticksPerStorageUpdate = objectLoadFrom.ticksPerStorageUpdate
    objectToLoad.ticksPerPageUpdate = objectLoadFrom.ticksPerPageUpdate
    objectToLoad.secondsPerSimulationTick = objectLoadFrom.secondsPerSimulationTick

    return objectToLoad

def loadSimulationEntry():
    #Load an entry from the simulation
    try:
        storedSim = StoredSimulation.objects.last()
        existingSimLoaded = True
    except:
        storedSim = StoredSimulation()
        existingSimLoaded = False
    return storedSim, existingSimLoaded

def loadSimulation(request, restartSimulation, storedSim, existingSimLoaded):
    #Create a PlanetarySimulationEngine() object
    if "simulationEngine" in request.session and restartSimulation == 0:
        # Load variables from session if they exist and the simulation isn't ordered to restart
        simulationEngine = request.session["simulationEngine"]
        setTicks = simulationEngine.ticksPerPageUpdate + simulationEngine.simulationTime
    elif existingSimLoaded and restartSimulation == 0:
        # If variables not found, load from the database instead (slower than loading from session)
        simulationEngine = PlanetarySimulationEngine()
        simulationEngine = loadValues(simulationEngine, storedSim)
        setTicks = simulationEngine.ticksPerPageUpdate + simulationEngine.simulationTime
    else:
        # If neither can be loaded or simulation ordered to restart,
        # load and initialise new simulation setup from template
        simulationEngine = PlanetarySimulationEngine()
        setTicks = 0
        if "templateIndex" in request.session:
            simulationEngine.loadTemplates(request.session["templateIndex"])
        else:
            # If template index isn't set, set to default value
            request.session["templateIndex"] = 0
            simulationEngine.loadTemplates(request.session["templateIndex"])
    return simulationEngine, setTicks


def runSimulation(request, restartSimulation = 0, autoRunSimulation = 0, reverseSimulation = 0):
    # The backend main loop for running the simulation - runs on every simulation page refresh

    # Load/create a database entry of the simulation
    storedSim, existingSimLoaded = loadSimulationEntry()

    # Load a PlanetarySimulationEngine() object
    simulationEngine, setTicks = loadSimulation(request, restartSimulation, storedSim, existingSimLoaded)

    if reverseSimulation == 0 or simulationEngine.simulationTime == 0:
        # Run instance of the simulation
        simulationEngine.runSimulation(setTicks)
        simulationInReverse = "No"
        invertedReverseSimulation = 1 # Used for switching on the HTML page
    else:
        # Run simulation in reverse if set to
        simulationEngine.rollbackSimulation()
        simulationInReverse = "Yes"
        invertedReverseSimulation = 0  # Used for switching on the HTML page

    # Store updated simulation
    request.session["simulationEngine"] = simulationEngine

    # Update database entry
    storedSim = loadValues(storedSim, simulationEngine)
    storedSim.save()

    # Calculate values for display
    daysElapsed = round((simulationEngine.simulationTime/86400)*simulationEngine.secondsPerSimulationTick, 2) # Simulation time in days
    daysPerTick = round((simulationEngine.ticksPerPageUpdate/86400)*simulationEngine.secondsPerSimulationTick, 2)
    statedSimulationSize = round(simulationEngine.simulationSize*1.495979e8) # Simulation diameter in kilometers
    fStatedSimulationSize = f"{statedSimulationSize:,}" #Adds commas to the number
    AUStatedSimulationSize = round(simulationEngine.simulationSize,3) # Calculates simulation diameter in Astronomical Units to 3DP

    # Package context for page
    context = {"simulationSizeKM": fStatedSimulationSize, "simulationSizeAU": AUStatedSimulationSize,
               "daysElapsed": daysElapsed, "daysPerTick": daysPerTick, "autoRunSimulation": autoRunSimulation,
               "reverseSimulation": reverseSimulation, "simulationInReverse": simulationInReverse, "invertedReverseSimulation": invertedReverseSimulation}

    return render(request, "runSimulationPage.html", context)