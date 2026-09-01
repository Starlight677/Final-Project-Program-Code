from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.shortcuts import render, redirect

from .forms import SimulationNameForm, BodyDetailsForm, LoginForm, RegisterForm
import matplotlib.colors as mcolors
from .models import StoredSimulation, UserProfile

from PlanetaryOrbitSimulator.twobodytesting import PlanetarySimulationEngine

def homePage(request):
    # Backend for the homepage
    user = request.user
    context = {"user": user}
    return render(request, "HomePage.html", context)

@login_required(login_url="/login/")
def settingsPage(request, styleIndex = -1):
    # Backend for the Settings page
    user = request.user
    styleBackgroundColours = ["black", "white", "none"]
    styleAxisColours = ["white", "black", "white"]
    styleDisplayNames = ["Dark Background", "Light Background", "Transparent Background"]

    if styleIndex == -1:
        # Note index of style chosen for the page
        styleIndex = styleBackgroundColours.index(request.session["backgroundStyle"])
    else:
        # If the page has chosen a style update the saved style
        request.session["backgroundStyle"] = styleBackgroundColours[styleIndex]
        request.session["axisStyle"] = styleAxisColours[styleIndex]

        profile = UserProfile.objects.get(user=user)
        profile.backgroundStylePreference = styleBackgroundColours[styleIndex]
        profile.axisStylePreference = styleAxisColours[styleIndex]
        profile.save()

    context = {"graphStyles": styleDisplayNames, "styleIndex": styleIndex}
    return render(request, "SettingsPage.html", context)

def loginPage(request):
    form = LoginForm(request.POST or None)
    if form.is_valid():
        if User.objects.filter(username=form.cleaned_data["username"]).exists():
            user = authenticate(username = form.cleaned_data["username"], password = form.cleaned_data["password"])
            if user is not None:
                login(request, user)

                # Get preferred style colour
                try:
                    profile = UserProfile.objects.get(user=user)
                except UserProfile.DoesNotExist:
                    profile = UserProfile(user=user)
                    profile.save()
                request.session["backgroundStyle"] = profile.backgroundStylePreference
                request.session["axisStyle"] = profile.axisStylePreference

                return redirect("/")
    return render(request, "LoginPage.html", {"loginForm": form, "currentUser": request.user})

def registerPage(request):
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        if not User.objects.filter(username=form.cleaned_data["username"]).exists():
            if form.cleaned_data["password"] == form.cleaned_data["passwordRepeated"]:
                user = User.objects.create_user(username=form.cleaned_data["username"], password=form.cleaned_data["password"])
                user.save()
                login(request, user)

    return render(request, "RegisterPage.html", {"registerForm": form, "currentUser": request.user})

@login_required(login_url="/login/")
def createPage(request, templateIndex = 0):
    # Backend for the Create New System page
    user = request.user
    request.session["templateIndex"] = templateIndex
    templatesList = ["Inner Solar System", "Galilean Moons of Jupiter", "Ascendia Primary Star", "Binary Stars", "Single Star"]

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

    simulationEngine.drawGraph(user, request.session["backgroundStyle"], request.session["axisStyle"])
    request.session["simulationEngine"] = simulationEngine

    # Wipe this field to stop previous simulation conflicts
    if "selectedSimulation" in request.session:
        del request.session["selectedSimulation"]

    context = {"templatesList": templatesList, "templateIndex": templateIndex, "form": form, "user": user}

    return render(request, "NewSystemPage.html", context)

@login_required(login_url="/login/")
def loadingPage(request, saveIndex = 0):
    # Backend for the Load Existing System page
    user = request.user
    if "templateIndex" not in request.session:
        # Test if index can be loaded - if not, set it to default
        request.session["templateIndex"] = 0

    try:
        # Try loading stored simulations
        allSimulations = StoredSimulation.objects.filter(user=user)
        allSimulations.order_by("pk")
        selectedSimulation = allSimulations[saveIndex]
        request.session["selectedSimulation"] = selectedSimulation

        simulationEngine, setTicks = loadSimulationEngine(request, selectedSimulation, True)

        selectedSimulation, simulationEngine, infoForm = makeSimulationForm(request, selectedSimulation, simulationEngine)

        simulationEngine.drawGraph(user, request.session["backgroundStyle"], request.session["axisStyle"])
        request.session["simulationEngine"] = simulationEngine

        # Create variables for display in information box
        daysElapsed = round((selectedSimulation.simulationTime / 86400) * selectedSimulation.secondsPerSimulationTick,
                            2)  # Simulation time in days
        daysPerTick = round(
            (selectedSimulation.ticksPerPageUpdate / 86400) * selectedSimulation.secondsPerSimulationTick, 2)
        statedSimulationSize = round(
            selectedSimulation.simulationSize * 1.495979e8)  # Simulation diameter in kilometers
        fStatedSimulationSize = f"{statedSimulationSize:,}"  # Adds commas to the distance number
        AUStatedSimulationSize = round(selectedSimulation.simulationSize,
                                       3)  # Calculates simulation diameter in Astronomical Units to 3DP
        context = {"allSimulations": allSimulations, "saveIndex": saveIndex, "name": selectedSimulation.name,
                   "daysElapsed": daysElapsed, "daysPerTick": daysPerTick, "simulationSizeKM": fStatedSimulationSize,
                   "simulationSizeAU": AUStatedSimulationSize, "infoForm": infoForm, "user": user}
    except:
        # If stored simulations can't be found, return blank array
        allSimulations = []
        selectedSimulation = []
        context = {"allSimulations": allSimulations, "selectedSimulation": selectedSimulation}

    return render(request, "LoadSystemPage.html", context)

def makeSimulationForm(request, storedSim, simulationEngine):
    simulationDefaultValues = {"simulationName": storedSim.name,
                               "simulationSize": simulationEngine.simulationSize,
                               "simulationTimePerUpdate": simulationEngine.ticksPerPageUpdate /
                                                          (86400 / simulationEngine.secondsPerSimulationTick), }
    infoForm = SimulationNameForm(request.POST or None,
                                  initial=simulationDefaultValues)  # Allow configuring information

    return storedSim, simulationEngine, infoForm

@login_required(login_url="/login/")
def editSimulationPage(request, selectedBody = 0):
    # For editing the simulation
    user = request.user
    # Load/create a database entry of the simulation
    storedSim, existingSimLoaded = loadSimulationEntry(request)

    # Load a PlanetarySimulationEngine() object (either from session/database or new from template)
    simulationEngine, setTicks = loadSimulationEngine(request, storedSim)

    #Generate useful context variables
    AU = 1.495979e11
    if selectedBody == len(simulationEngine.listOfBodies):
        bodyDisplayDetails = {"bodyMass": 0,
                              "bodyColour": "White",
                              "bodyName": "Add New Body",
                              "bodyRadius": 0,
                              "bodyXPosition": 0,
                              "bodyYPosition": 0,
                              "bodyXSpeed": 0,
                              "bodyYSpeed": 0, }
    else:
        # Round unnecessary precision before displaying to the user
        bodyDisplayDetails = {"bodyMass": roundToSignificantFigures(simulationEngine.listOfBodies[selectedBody][2],4),
                              "bodyColour": simulationEngine.listOfBodies[selectedBody][4][0],
                              "bodyName": simulationEngine.listOfBodies[selectedBody][5],
                              "bodyRadius": round(simulationEngine.listOfBodies[selectedBody][3]/1000,3),
                              "bodyXPosition": roundToSignificantFigures(simulationEngine.listOfBodies[selectedBody][0][0]/AU,6),
                              "bodyYPosition": roundToSignificantFigures(simulationEngine.listOfBodies[selectedBody][0][1]/AU,6),
                              "bodyXSpeed": round(simulationEngine.listOfBodies[selectedBody][1][0]/1000,3),
                              "bodyYSpeed": round(simulationEngine.listOfBodies[selectedBody][1][1]/1000,3),}
    detailsForm = BodyDetailsForm(request.POST or None, initial=bodyDisplayDetails)

    # Focus the screen on the selected body
    if selectedBody < len(simulationEngine.listOfBodies):
        simulationEngine.focusBody = selectedBody
    else:
        simulationEngine.focusBody = -1

    # Display graph and save any edits
    simulationEngine.drawGraph(user, request.session["backgroundStyle"], request.session["axisStyle"])
    request.session["simulationEngine"] = simulationEngine
    storedSim = loadValues(storedSim, simulationEngine)
    storedSim.save()

    # Calculate values for display
    daysElapsed = round((simulationEngine.simulationTime / 86400) * simulationEngine.secondsPerSimulationTick,2)  # Simulation time in days
    daysPerTick = round((simulationEngine.ticksPerPageUpdate / 86400) * simulationEngine.secondsPerSimulationTick, 2)
    statedSimulationSize = round(simulationEngine.simulationSize * 1.495979e8)  # Simulation diameter in kilometers
    fStatedSimulationSize = f"{statedSimulationSize:,}"  # Adds commas to the number
    AUStatedSimulationSize = round(simulationEngine.simulationSize,3)  # Calculates simulation diameter in Astronomical Units to 3DP

    # Calculate next and previous bodies
    if selectedBody >= len(simulationEngine.listOfBodies):
        nextBody = selectedBody
        lastBody = selectedBody - 1
    elif selectedBody <= 0:
        nextBody = selectedBody + 1
        lastBody = selectedBody
    else:
        nextBody = selectedBody + 1
        lastBody = selectedBody - 1

    # Package context for page
    context = {"simulationSizeKM": fStatedSimulationSize, "simulationSizeAU": AUStatedSimulationSize,
               "daysElapsed": daysElapsed, "daysPerTick": daysPerTick, "selectedBody": selectedBody,
               "nextBody": nextBody, "lastBody": lastBody, "detailsForm": detailsForm,
               "simulationName": storedSim.name, "focusBodyName": simulationEngine.focusBodyName,
               "user": user}

    return render(request, "editSystemPage.html", context)


def roundToSignificantFigures(number, significiantFigures):
    # Modified version of a function from IDiTect.com
    # Article at: https://www.iditect.com/faq/python/how-to-round-a-number-to-significant-figures-in-python.html
    formattedNumber = "{:.{}g}".format(number, significiantFigures)
    # Convert the formatted string back to a floating-point number
    roundedNumber = float(formattedNumber)
    return roundedNumber

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

def loadSimulationEntry(request):
    #Load an entry from the simulation
    if "selectedSimulation" in request.session:
        # Use existing save if found
        existingSimLoaded = True
    elif "simulationEngine" in request.session:
        # If not, create new save
        request.session["selectedSimulation"] = StoredSimulation(name=request.session["simulationEngine"].simulationName)
        existingSimLoaded = False
    else:
        # If no name for new save, use placeholder
        request.session["selectedSimulation"] = StoredSimulation(name="No name found")
        existingSimLoaded = False
    # Load save
    storedSim = request.session["selectedSimulation"]
    return storedSim, existingSimLoaded

def loadSimulationEngine(request, storedSim, forceLoad=False):
    # Create a PlanetarySimulationEngine() object
    if "simulationEngine" in request.session and not forceLoad:
        # Load variables from session if they exist
        simulationEngine = request.session["simulationEngine"]
        setTicks = simulationEngine.ticksPerPageUpdate + simulationEngine.simulationTime
    else:
        # If variables not found in session, load from the database instead
        simulationEngine = PlanetarySimulationEngine()
        simulationEngine = loadValues(simulationEngine, storedSim)
        setTicks = simulationEngine.ticksPerPageUpdate + simulationEngine.simulationTime
    return simulationEngine, setTicks

def runSimulationTick(request, simulationEngine, storedSim, reverseSimulation, dontRunSimulation, setTicks):
    user = request.user
    if (reverseSimulation == 0 or simulationEngine.simulationTime == 0) and dontRunSimulation == 0:
        # Run instance of the simulation if not initially loaded
        simulationEngine.runSimulation(user, request.session["backgroundStyle"], request.session["axisStyle"], setTicks)
        isSimulationInReverse = "No"
    elif dontRunSimulation == 0:
        # Run simulation in reverse if set to
        simulationEngine.rollbackSimulation(user, request.session["backgroundStyle"], request.session["axisStyle"])
        isSimulationInReverse = "Yes"
    else:
        # If simulation just being loaded, only draw graph
        simulationEngine.drawGraph(user, request.session["backgroundStyle"], request.session["axisStyle"])
        isSimulationInReverse = "No" # Text description for display

    # Store updated simulation in session variable
    request.session["simulationEngine"] = simulationEngine

    # Update database entry for simulation
    storedSim = loadValues(storedSim, simulationEngine)
    storedSim.user = user
    storedSim.save()

    return storedSim, simulationEngine, isSimulationInReverse

# The backend main loop for running the simulation - runs on every simulation page refresh
@login_required(login_url="/login/")
def runSimulation(request, dontRunSimulation = 0, reverseSimulation = 0):
    # Load/create a database entry of the simulation
    storedSim, existingSimLoaded = loadSimulationEntry(request)

    # Load a PlanetarySimulationEngine() object (either from session/database or new from template)
    simulationEngine, setTicks = loadSimulationEngine(request, storedSim)

    storedSim, simulationEngine, infoForm = makeSimulationForm(request, storedSim, simulationEngine)

    storedSim, simulationEngine, isSimulationInReverse, = (
        runSimulationTick(request, simulationEngine, storedSim, reverseSimulation, dontRunSimulation, setTicks))

    # Calculate values for display
    daysElapsed = round((simulationEngine.simulationTime/86400)*simulationEngine.secondsPerSimulationTick, 2) # Simulation time in days
    daysPerTick = round((simulationEngine.ticksPerPageUpdate/86400)*simulationEngine.secondsPerSimulationTick, 2)
    statedSimulationSize = round(simulationEngine.simulationSize*1.495979e8) # Simulation diameter in kilometers
    fStatedSimulationSize = f"{statedSimulationSize:,}" #Adds commas to the number
    AUStatedSimulationSize = round(simulationEngine.simulationSize,3) # Calculates simulation diameter in Astronomical Units to 3DP

    # Package context for page
    context = {"simulationSizeKM": fStatedSimulationSize, "simulationSizeAU": AUStatedSimulationSize,
               "daysElapsed": daysElapsed, "daysPerTick": daysPerTick, "isSimulationInReverse": isSimulationInReverse,
               "simulationName": storedSim.name, "focusBodyName": simulationEngine.focusBodyName,
               "infoForm": infoForm,}

    constructedResponse = render(request, "runSimulationPage.html", context)
    return constructedResponse

@login_required(login_url="/login/")
def stopSimulation(request, reverseSimulation):
    # Load/create a database entry of the simulation
    storedSim, existingSimLoaded = loadSimulationEntry(request)

    # Load a PlanetarySimulationEngine() object (either from session/database or new from template)
    simulationEngine, setTicks = loadSimulationEngine(request, storedSim)

    runSimulationTick(request, simulationEngine, storedSim, 0, 1, setTicks)

    context = {"reverseSimulation": reverseSimulation}
    return render(request, "stopSimulationPage.html", context)

def updateSimulationImage(request, reverseSimulation = 0):
    user = request.user
    # Load/create a database entry of the simulation
    storedSim, existingSimLoaded = loadSimulationEntry(request)

    # Load a PlanetarySimulationEngine() object (either from session/database or new from template)
    simulationEngine, setTicks = loadSimulationEngine(request, storedSim)

    storedSim, simulationEngine, isSimulationInReverse = (
        runSimulationTick(request, simulationEngine, storedSim, reverseSimulation, 0, setTicks))

    daysElapsed = round((simulationEngine.simulationTime / 86400) * simulationEngine.secondsPerSimulationTick, 2)  # Simulation time in days
    constructedResponse = JsonResponse({"daysElapsed": daysElapsed, "isSimulationInReverse": isSimulationInReverse})
    return constructedResponse

def changeSimulationFocus(request):
    user = request.user
    # Load/create a database entry of the simulation
    storedSim, existingSimLoaded = loadSimulationEntry(request)

    # Load a PlanetarySimulationEngine() object (either from session/database or new from template)
    simulationEngine, setTicks = loadSimulationEngine(request, storedSim)

    simulationEngine.focusBody = simulationEngine.focusBody + 1
    simulationEngine.updateFocusPoint()

    runSimulationTick(request, simulationEngine, storedSim, 0, 1, setTicks)

    updatedImageURL = "/media/latestSimulation" + user.username + ".jpeg"
    constructedResponse = JsonResponse({"updatedImageURL": updatedImageURL, "focusBodyName": simulationEngine.focusBodyName})
    return constructedResponse

def processRunForm(request, isCreating = 0):
    user = request.user
    # Load/create a database entry of the simulation
    storedSim, existingSimLoaded = loadSimulationEntry(request)

    # Load a PlanetarySimulationEngine() object (either from session/database or new from template)
    simulationEngine, setTicks = loadSimulationEngine(request, storedSim)

    runForm = SimulationNameForm(request.POST)

    if runForm.is_valid():
        storedSim.name = runForm.cleaned_data["simulationName"]
        simulationEngine.simulationSize = runForm.cleaned_data["simulationSize"]
        adjustedTimePerTick =  round(runForm.cleaned_data["simulationTimePerUpdate"] * 86400)
        simulationEngine.ticksPerPageUpdate = adjustedTimePerTick  / simulationEngine.secondsPerSimulationTick
    else:
        raise ValueError

    simulationEngine.drawGraph(user, request.session["backgroundStyle"], request.session["axisStyle"])

    #Update stored simulation data
    if isCreating == 0:
        request.session["simulationEngine"] = simulationEngine
        storedSim = loadValues(storedSim, simulationEngine)
        storedSim.user = user
        storedSim.save()

    # Calculate values for display
    daysPerTick = round((simulationEngine.ticksPerPageUpdate / 86400) * simulationEngine.secondsPerSimulationTick, 2)
    statedSimulationSize = round(simulationEngine.simulationSize * 1.495979e8)  # Simulation diameter in kilometers
    fStatedSimulationSize = f"{statedSimulationSize:,}"  # Adds commas to the number
    AUStatedSimulationSize = round(simulationEngine.simulationSize,
                                   3)  # Calculates simulation diameter in Astronomical Units to 3DP

    response = {"simulationName": storedSim.name, "daysPerTick": daysPerTick, "simulationSizeAU": AUStatedSimulationSize,
                "simulationSizeKM": fStatedSimulationSize}
    return JsonResponse(response)

def processEditForm(request, selectedBody):
    user = request.user
    # Load/create a database entry of the simulation
    storedSim, existingSimLoaded = loadSimulationEntry(request)

    # Load a PlanetarySimulationEngine() object (either from session/database or new from template)
    simulationEngine, setTicks = loadSimulationEngine(request, storedSim)

    detailsForm = BodyDetailsForm(request.POST)

    AU = 1.495979e11
    if detailsForm.is_valid():
        # Load parameters from form
        if selectedBody == len(simulationEngine.listOfBodies):
            # If creating new body, add empty framework to list
            simulationEngine.listOfBodies.append([[0, 0, 0], [0, 0, 0], 0, 0, ['white', 'white'], ""])
            simulationEngine.bodyPoints.append([[], [], [[],[],[]]])

        simulationEngine.listOfBodies[selectedBody][2] = detailsForm.cleaned_data["bodyMass"]
        simulationEngine.listOfBodies[selectedBody][3] = detailsForm.cleaned_data["bodyRadius"]
        simulationEngine.listOfBodies[selectedBody][5] = detailsForm.cleaned_data["bodyName"]

        simulationEngine.listOfBodies[selectedBody][0][0] = detailsForm.cleaned_data["bodyXPosition"]*AU
        simulationEngine.listOfBodies[selectedBody][0][1] = detailsForm.cleaned_data["bodyYPosition"]*AU
        simulationEngine.listOfBodies[selectedBody][1][0] = detailsForm.cleaned_data["bodyXSpeed"]*1000
        simulationEngine.listOfBodies[selectedBody][1][1] = detailsForm.cleaned_data["bodyYSpeed"]*1000

        if detailsForm.cleaned_data["bodyColour"] in mcolors.CSS4_COLORS:
            # Only update colour if valid colour entered
            simulationEngine.listOfBodies[selectedBody][4][0] = detailsForm.cleaned_data["bodyColour"]
            simulationEngine.listOfBodies[selectedBody][4][1] = detailsForm.cleaned_data["bodyColour"] # Update both colour fields
        else:
            print("Invalid colour!")
    else:
        raise ValueError

    simulationEngine.drawGraph(user, request.session["backgroundStyle"], request.session["axisStyle"])

    #Update stored simulation data
    request.session["simulationEngine"] = simulationEngine
    storedSim = loadValues(storedSim, simulationEngine)
    storedSim.user = user
    storedSim.save()

    response = {}
    return JsonResponse(response)

