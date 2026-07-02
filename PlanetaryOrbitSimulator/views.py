from django.shortcuts import render
from .forms import SimulationNameForm

from.models import StoredSimulation

from PlanetaryOrbitSimulator.twobodytesting import PlanetarySimulationEngine

def homePage(request):
    # Backend for the homepage
    context = {}
    return render(request, "HomePage.html", context)

def settingsPage(request):
    # Backend for the Settings page
    context = {}
    return render(request, "SettingsPage.html", context)

def createPage(request, templateIndex = 0):
    # Backend for the Create New System page
    request.session["templateIndex"] = templateIndex
    templatesList = ["Inner Solar System", "Galilean Moons of Jupiter", "Ascendia Primary Star", "Single Star"]

    # Load a Planetary Simulation Engine for accessing parameters
    simulationEngine = PlanetarySimulationEngine()
    simulationEngine.loadTemplates(templateIndex)
    simulationTimePerTick = simulationEngine.ticksPerPageUpdate * simulationEngine.secondsPerSimulationTick
    simulationTimePerTick = simulationTimePerTick / 86400 # Give the time per tick in days, not seconds

    # Get details of new simulation from user with a form
    simulationDefaultValues = {"simulationName": simulationEngine.simulationName,
                               "simulationSize": simulationEngine.simulationSize,
                               "simulationTimePerUpdate": simulationTimePerTick,}
    form = SimulationNameForm(request.POST or None, initial=simulationDefaultValues)

    if form.is_valid():
        # Load parameters from form
        simulationEngine.simulationName = form.cleaned_data["simulationName"]
        simulationEngine.simulationSize = form.cleaned_data["simulationSize"]
        adjustedTimePerTick = round(form.cleaned_data["simulationTimePerUpdate"] * 86400)
        simulationEngine.ticksPerPageUpdate = adjustedTimePerTick/simulationEngine.secondsPerSimulationTick
    request.session["simulationEngine"] = simulationEngine

    # Wipe this field to stop previous simulation conflicts
    if "selectedSimulation" in request.session:
        del request.session["selectedSimulation"]

    context = {"templatesList": templatesList, "templateIndex": templateIndex, "form": form}

    return render(request, "NewSystemPage.html", context)

def loadingPage(request, saveIndex = 0):
    # Backend for the Load Existing System page
    if "templateIndex" not in request.session:
        # Test if index can be loaded - if not, set it to default
        request.session["templateIndex"] = 0

    try:
        # Try loading stored simulations
        allSimulations = StoredSimulation.objects.all()
        allSimulations.order_by("pk")
        selectedSimulation = allSimulations[saveIndex]
        request.session["selectedSimulation"] = selectedSimulation
    except:
        # If stored simulations can't be found, return blank array
        allSimulations = []
        selectedSimulation = []

    # Wipe this field to stop previous simulations carrying over
    if "simulationEngine" in request.session:
        del request.session["simulationEngine"]

    # Create variables for display in information box
    daysElapsed = round((selectedSimulation.simulationTime / 86400) * selectedSimulation.secondsPerSimulationTick,
                        2)  # Simulation time in days
    daysPerTick = round((selectedSimulation.ticksPerPageUpdate / 86400) * selectedSimulation.secondsPerSimulationTick, 2)
    statedSimulationSize = round(selectedSimulation.simulationSize * 1.495979e8)  # Simulation diameter in kilometers
    fStatedSimulationSize = f"{statedSimulationSize:,}"  # Adds commas to the distance number
    AUStatedSimulationSize = round(selectedSimulation.simulationSize,
                                   3)  # Calculates simulation diameter in Astronomical Units to 3DP
    context = {"allSimulations": allSimulations, "saveIndex": saveIndex, "name": selectedSimulation.name,
               "daysElapsed": daysElapsed, "daysPerTick": daysPerTick, "simulationSizeKM": fStatedSimulationSize,
               "simulationSizeAU": AUStatedSimulationSize}
    return render(request, "LoadSystemPage.html", context)

# Here starts methods used for runSimulation()

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

def loadSimulationEntry(request, restartSimulation):
    #Load an entry from the simulation
    if "selectedSimulation" in request.session and restartSimulation == 0:
        # Load selected save if found and not ordered to restart
        storedSim = request.session["selectedSimulation"]
        existingSimLoaded = True
    elif "simulationEngine" in request.session:
        # If name for new save can be found (from stored simulationEngine), use it
        request.session["selectedSimulation"] = StoredSimulation(name=request.session["simulationEngine"].simulationName)
        storedSim = request.session["selectedSimulation"]
        request.session["selectedSimulationIndex"] = storedSim.pk
        existingSimLoaded = False
    else:
        # If no name, use placeholder
        request.session["selectedSimulation"] = StoredSimulation(name="No name found")
        storedSim = request.session["selectedSimulation"]
        request.session["selectedSimulationIndex"] = storedSim.pk
        existingSimLoaded = False
    return storedSim, existingSimLoaded

def loadSimulationEngine(request, storedSim):
    # Create a PlanetarySimulationEngine() object
    if "simulationEngine" in request.session:
        # Load variables from session if they exist and the simulation isn't ordered to restart
        simulationEngine = request.session["simulationEngine"]
        setTicks = simulationEngine.ticksPerPageUpdate + simulationEngine.simulationTime
    else:
        # If variables not found, load from the database instead (slower than loading from session)
        simulationEngine = PlanetarySimulationEngine()
        simulationEngine = loadValues(simulationEngine, storedSim)
        setTicks = simulationEngine.ticksPerPageUpdate + simulationEngine.simulationTime
    return simulationEngine, setTicks

# The backend main loop for running the simulation - runs on every simulation page refresh
def runSimulation(request, restartSimulation = 0, autoRunSimulation = 0, reverseSimulation = 0):
    # Load/create a database entry of the simulation
    storedSim, existingSimLoaded = loadSimulationEntry(request, restartSimulation)

    # Load a PlanetarySimulationEngine() object (either from session/database or new from template)
    simulationEngine, setTicks = loadSimulationEngine(request, storedSim)

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