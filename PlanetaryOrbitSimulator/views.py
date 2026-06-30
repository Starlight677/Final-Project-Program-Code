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
    templatesList = ["Inner Solar System", "Galilean Moons of Jupiter", "Ascendia A Star"]
    context = {"templatesList": templatesList, "templateIndex": templateIndex}
    return render(request, "NewSystemPage.html", context)

def loadingPage(request):
    try:
        templateIndex = request.session["templateIndex"]
    except:
        request.session["templateIndex"] = 0
    context = {}
    return render(request, "LoadSystemPage.html", context)

def runSimulation(request, restartSimulation = 0, autoRunSimulation = 0, reverseSimulation = 0):
    if "simulationEngine" in request.session: # Load variables from session if they exist, otherwise set to starting values
        simulationEngine = request.session["simulationEngine"]
        setTicks = simulationEngine.ticksPerPageUpdate + simulationEngine.simulationTime
    else:
        # If variables not found, start new session
        restartSimulation = 1

    if restartSimulation == 1:
        # Load and initialise new simulation setup from template
        simulationEngine = PlanetarySimulationEngine()
        setTicks = 0
        try: # If template index isn't set, set to default value
            simulationEngine.loadTemplates(request.session["templateIndex"])
        except:
            request.session["templateIndex"] = 0
            simulationEngine.loadTemplates(request.session["templateIndex"])

    if reverseSimulation == 0 or simulationEngine.simulationTime == 0:
        # Run instance of the simulation
        simulationEngine.runSimulation(setTicks)
        simulationInReverse = "No"
        invertedReverseSimulation = 1 # Used for switching on the HTML page
    else:
        simulationEngine.rollbackSimulation()
        simulationInReverse = "Yes"
        invertedReverseSimulation = 0  # Used for switching on the HTML page

    #Store updated simulation
    request.session["simulationEngine"] = simulationEngine

    daysElapsed = round((simulationEngine.simulationTime/86400)*simulationEngine.secondsPerSimulationTick, 2) # Simulation time in days
    daysPerTick = round((simulationEngine.ticksPerPageUpdate/86400)*simulationEngine.secondsPerSimulationTick, 2)
    statedSimulationSize = round(simulationEngine.simulationSize*1.495979e8) # Simulation diameter in kilometers
    fStatedSimulationSize = f"{statedSimulationSize:,}" #Adds commas to the number
    AUStatedSimulationSize = round(simulationEngine.simulationSize,3) # Calculates simulation diameter in Astronomical Units to 3DP

    context = {"simulationSizeKM": fStatedSimulationSize, "simulationSizeAU": AUStatedSimulationSize,
               "daysElapsed": daysElapsed, "daysPerTick": daysPerTick, "autoRunSimulation": autoRunSimulation,
               "reverseSimulation": reverseSimulation, "simulationInReverse": simulationInReverse, "invertedReverseSimulation": invertedReverseSimulation}

    return render(request, "runSimulationPage.html", context)