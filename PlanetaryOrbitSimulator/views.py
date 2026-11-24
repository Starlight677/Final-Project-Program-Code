import matplotlib.colors as mcolors
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render

from PlanetaryOrbitSimulator.planetarySimulationEngine import (
    AU_METERS,
    COLOUR,
    MASS,
    NAME,
    POS,
    RADIUS,
    SECONDS_PER_DAY,
    TEMPLATE_NAMES,
    VEL,
    PlanetarySimulationEngine,
)
from .forms import BodyDetailsForm, LoginForm, RegisterForm, SimulationNameForm
from .models import StoredSimulation, UserProfile

AU_KM = AU_METERS / 1000
GRAPH_STYLES = (
    ("Dark Background", "black", "white"),
    ("Light Background", "white", "black"),
    ("Transparent Background", "none", "white"),
)
SIMULATION_FIELDS = (
    "simulationTime",
    "simulationSize",
    "listOfBodies",
    "bodyPoints",
    "ticksPerStorageUpdate",
    "ticksPerPageUpdate",
    "secondsPerSimulationTick",
)


def _roundSigFigs(number, sigFigs):
    return float(f"{number:.{sigFigs}g}")


def _loadStyleIntoSession(request, user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    request.session["backgroundStyle"] = profile.backgroundStylePreference
    request.session["axisStyle"] = profile.axisStylePreference
    return profile


def _getStylePreferences(request):
    if "backgroundStyle" not in request.session or "axisStyle" not in request.session:
        _loadStyleIntoSession(request, request.user)
    return request.session["backgroundStyle"], request.session["axisStyle"]


def _copySimulationFields(target, source):
    for field in SIMULATION_FIELDS:
        setattr(target, field, getattr(source, field))
    return target


def _getActiveSimulation(request):
    engine = request.session.get("simulationEngine")
    storedSim = request.session.get("selectedSimulation")
    if storedSim is None:
        simName = engine.simulationName if engine is not None else "No name found"
        storedSim = StoredSimulation(name=simName, user=request.user)
        request.session["selectedSimulation"] = storedSim
    if engine is None:
        engine = _copySimulationFields(PlanetarySimulationEngine(), storedSim)
        engine.simulationName = storedSim.name
    return storedSim, engine


def _saveSimulationState(request, storedSim, engine, saveToDb=True, drawGraph=True):
    if drawGraph:
        bgStyle, axisStyle = _getStylePreferences(request)
        engine.drawGraph(request.user, bgStyle, axisStyle)
    request.session["simulationEngine"] = engine
    request.session["selectedSimulation"] = storedSim
    _copySimulationFields(storedSim, engine)
    storedSim.user = request.user
    if saveToDb:
        storedSim.save()


def _getBodyChoices(engine, noneLabel="None", excludeIndex=None):
    return [(-1, noneLabel)] + [
        (i, b[NAME]) for i, b in enumerate(engine.listOfBodies) if i != excludeIndex
    ]


def _getDisplayMetrics(sim):
    dtRatio = sim.secondsPerSimulationTick / SECONDS_PER_DAY
    return {
        "daysElapsed": round(sim.simulationTime * dtRatio, 2),
        "daysPerTick": round(sim.ticksPerPageUpdate * dtRatio, 2),
        "simulationSizeKM": f"{round(sim.simulationSize * AU_KM):,}",
        "simulationSizeAU": round(sim.simulationSize, 3),
    }


def _buildSimulationForm(request, simulationName, engine, includeFocusBody=False):
    initial = {
        "simulationName": simulationName,
        "simulationSize": engine.simulationSize,
        "simulationTimePerUpdate": (engine.ticksPerPageUpdate * engine.secondsPerSimulationTick) / SECONDS_PER_DAY,
    }
    bodyChoices = None
    if includeFocusBody:
        bodyChoices = _getBodyChoices(engine)
        initial["focusedBody"] = engine.focusBody
    return SimulationNameForm(request.POST or None, initial=initial, body_choices=bodyChoices)


def _stepSimulation(request, storedSim, engine, reverseSimulation=0, dontRunSimulation=0):
    bgStyle, axisStyle = _getStylePreferences(request)
    isReverse = "No"
    if dontRunSimulation != 0:
        engine.drawGraph(request.user, bgStyle, axisStyle)
    elif reverseSimulation == 0:
        setTicks = engine.ticksPerPageUpdate + engine.simulationTime
        engine.runSimulation(request.user, bgStyle, axisStyle, setTicks)
    else:
        if engine.simulationTime > 0:
            engine.rollbackSimulation(request.user, bgStyle, axisStyle)
        isReverse = "Yes"

    _saveSimulationState(request, storedSim, engine, drawGraph=False)
    return isReverse


def homePage(request):
    return render(request, "HomePage.html")


@login_required(login_url="/login/")
def settingsPage(request, styleIndex=-1):
    bgColours = [bg for _, bg, _ in GRAPH_STYLES]
    if 0 <= styleIndex < len(GRAPH_STYLES):
        _, bg, axis = GRAPH_STYLES[styleIndex]
        request.session["backgroundStyle"] = bg
        request.session["axisStyle"] = axis
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.backgroundStylePreference = bg
        profile.axisStylePreference = axis
        profile.save()
    else:
        bgStyle, _ = _getStylePreferences(request)
        styleIndex = bgColours.index(bgStyle) if bgStyle in bgColours else 0

    return render(request, "SettingsPage.html", {
        "graphStyles": [label for label, _, _ in GRAPH_STYLES],
        "styleIndex": styleIndex,
    })


def loginPage(request):
    form = LoginForm(request.POST or None)
    if form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user is not None:
            login(request, user)
            _loadStyleIntoSession(request, user)
            return redirect("/")
    return render(request, "LoginPage.html", {"loginForm": form})


def registerPage(request):
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        if password == form.cleaned_data["passwordRepeated"] and not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            _loadStyleIntoSession(request, user)
    return render(request, "RegisterPage.html", {"registerForm": form})


@login_required(login_url="/login/")
def createPage(request, templateIndex=0):
    engine = PlanetarySimulationEngine()
    engine.loadTemplates(templateIndex)

    form = _buildSimulationForm(request, engine.simulationName, engine)
    bgStyle, axisStyle = _getStylePreferences(request)
    engine.drawGraph(request.user, bgStyle, axisStyle)
    request.session["simulationEngine"] = engine
    request.session.pop("selectedSimulation", None)

    return render(request, "NewSystemPage.html", {
        "templatesList": TEMPLATE_NAMES,
        "templateIndex": templateIndex,
        "form": form,
    })


@login_required(login_url="/login/")
def loadingPage(request, saveIndex=0):
    allSimulations = list(StoredSimulation.objects.filter(user=request.user).order_by("pk"))
    if not allSimulations or not (0 <= saveIndex < len(allSimulations)):
        return render(request, "HomePage.html")

    selectedSimulation = allSimulations[saveIndex]
    request.session["selectedSimulation"] = selectedSimulation

    engine = _copySimulationFields(PlanetarySimulationEngine(), selectedSimulation)
    engine.simulationName = selectedSimulation.name
    infoForm = _buildSimulationForm(request, selectedSimulation.name, engine)

    bgStyle, axisStyle = _getStylePreferences(request)
    engine.drawGraph(request.user, bgStyle, axisStyle)
    request.session["simulationEngine"] = engine

    return render(request, "LoadSystemPage.html", {
        "allSimulations": allSimulations,
        "saveIndex": saveIndex,
        "name": selectedSimulation.name,
        "infoForm": infoForm,
        **_getDisplayMetrics(engine),
    })


@login_required(login_url="/login/")
def editSimulationPage(request, selectedBody=0):
    storedSim, engine = _getActiveSimulation(request)
    numBodies = len(engine.listOfBodies)
    selectedBody = max(0, min(selectedBody, numBodies))

    bodyChoices = _getBodyChoices(engine, "None (Static Grid)", excludeIndex=selectedBody)
    if selectedBody == numBodies:
        bodyDetails = {
            "bodyMass": 0,
            "bodyColour": "White",
            "bodyName": "Add New Body",
            "bodyRadius": 0,
            "bodyReference": -1,
            "bodyXPosition": 0,
            "bodyYPosition": 0,
            "bodyXSpeed": 0,
            "bodyYSpeed": 0,
        }
        engine.focusBody = -1
    else:
        body = engine.listOfBodies[selectedBody]
        colour = body[COLOUR][0] if isinstance(body[COLOUR], list) else body[COLOUR]
        bodyDetails = {
            "bodyMass": _roundSigFigs(body[MASS], 4),
            "bodyColour": colour,
            "bodyName": body[NAME],
            "bodyRadius": round(body[RADIUS] / 1000, 3),
            "bodyReference": engine.getBodyReference(selectedBody),
            "bodyXPosition": _roundSigFigs(body[POS][0] / AU_METERS, 6),
            "bodyYPosition": _roundSigFigs(body[POS][1] / AU_METERS, 6),
            "bodyXSpeed": round(body[VEL][0] / 1000, 3),
            "bodyYSpeed": round(body[VEL][1] / 1000, 3),
        }
        engine.focusBody = selectedBody

    detailsForm = BodyDetailsForm(request.POST or None, initial=bodyDetails, body_choices=bodyChoices)
    _saveSimulationState(request, storedSim, engine)

    return render(request, "editSystemPage.html", {
        **_getDisplayMetrics(engine),
        "selectedBody": selectedBody,
        "nextBody": min(selectedBody + 1, numBodies),
        "lastBody": max(selectedBody - 1, 0),
        "detailsForm": detailsForm,
        "simulationName": storedSim.name,
        "focusBodyName": engine.focusBodyName,
    })


@login_required(login_url="/login/")
def runSimulation(request, dontRunSimulation=0, reverseSimulation=0):
    storedSim, engine = _getActiveSimulation(request)
    isReverse = _stepSimulation(request, storedSim, engine, reverseSimulation, dontRunSimulation)
    infoForm = _buildSimulationForm(request, storedSim.name, engine, includeFocusBody=True)

    return render(request, "RunSimulationPage.html", {
        **_getDisplayMetrics(engine),
        "isSimulationInReverse": isReverse,
        "simulationName": storedSim.name,
        "focusBodyName": engine.focusBodyName,
        "infoForm": infoForm,
    })


@login_required(login_url="/login/")
def updateSimulationImage(request, reverseSimulation=0):
    storedSim, engine = _getActiveSimulation(request)
    isReverse = _stepSimulation(request, storedSim, engine, reverseSimulation, dontRunSimulation=0)

    return JsonResponse({
        "daysElapsed": _getDisplayMetrics(engine)["daysElapsed"],
        "isSimulationInReverse": isReverse,
        "focusBody": engine.focusBody,
        "focusBodyName": engine.focusBodyName,
        "focusChoices": _getBodyChoices(engine),
    })


@login_required(login_url="/login/")
def changeSimulationFocus(request):
    storedSim, engine = _getActiveSimulation(request)
    engine.focusBody += 1
    engine.updateFocusPoint()
    _saveSimulationState(request, storedSim, engine)

    relativeBodyName = (
        engine.getBodyReferenceName(engine.focusBody)
        if engine.focusBody != -1 else "None (Static Grid)"
    )
    return JsonResponse({
        "updatedImageURL": f"/media/latestSimulation{request.user.username}.png",
        "focusBody": engine.focusBody,
        "focusBodyName": engine.focusBodyName,
        "relativeBodyName": relativeBodyName,
    })


@login_required(login_url="/login/")
def processRunForm(request, isCreating=0):
    storedSim, engine = _getActiveSimulation(request)
    runForm = SimulationNameForm(request.POST, body_choices=_getBodyChoices(engine))
    if not runForm.is_valid():
        return JsonResponse({"error": "Invalid form data"}, status=400)

    cleaned = runForm.cleaned_data
    if cleaned.get("simulationName"):
        storedSim.name = cleaned["simulationName"]
        engine.simulationName = storedSim.name
    if cleaned.get("simulationSize") is not None:
        engine.simulationSize = cleaned["simulationSize"]
    if cleaned.get("simulationTimePerUpdate") is not None and engine.secondsPerSimulationTick > 0:
        adjustedSeconds = round(cleaned["simulationTimePerUpdate"] * SECONDS_PER_DAY)
        engine.ticksPerPageUpdate = round(adjustedSeconds / engine.secondsPerSimulationTick)

    focusedBodyVal = cleaned.get("focusedBody")
    if focusedBodyVal not in (None, ""):
        engine.focusBody = int(focusedBodyVal)
        engine.updateFocusPoint()

    _saveSimulationState(request, storedSim, engine, saveToDb=(isCreating == 0))
    metrics = _getDisplayMetrics(engine)

    return JsonResponse({
        "simulationName": storedSim.name,
        "daysPerTick": metrics["daysPerTick"],
        "simulationSizeAU": metrics["simulationSizeAU"],
        "simulationSizeKM": metrics["simulationSizeKM"],
        "focusBody": engine.focusBody,
        "focusBodyName": engine.focusBodyName,
    })


@login_required(login_url="/login/")
def processEditForm(request, selectedBody):
    storedSim, engine = _getActiveSimulation(request)
    if selectedBody < 0 or selectedBody > len(engine.listOfBodies):
        return JsonResponse({"error": "Body index out of range"}, status=400)

    bodyChoices = _getBodyChoices(engine, "None (Static Grid)", excludeIndex=selectedBody)
    detailsForm = BodyDetailsForm(request.POST, body_choices=bodyChoices)
    if not detailsForm.is_valid():
        return JsonResponse({"error": "Invalid form data"}, status=400)

    cleaned = detailsForm.cleaned_data
    if selectedBody == len(engine.listOfBodies):
        engine.listOfBodies.append([[0, 0, 0], [0, 0, 0], 0, 0, ["white", "white"], "", -1])
        engine.bodyPoints.append([[], [], [[], [], []]])

    body = engine.listOfBodies[selectedBody]
    if cleaned.get("bodyMass") is not None:
        body[MASS] = cleaned["bodyMass"]
    if cleaned.get("bodyRadius") is not None:
        body[RADIUS] = cleaned["bodyRadius"] * 1000
    if cleaned.get("bodyName") is not None:
        body[NAME] = cleaned["bodyName"]
    if cleaned.get("bodyXPosition") is not None:
        body[POS][0] = cleaned["bodyXPosition"] * AU_METERS
    if cleaned.get("bodyYPosition") is not None:
        body[POS][1] = cleaned["bodyYPosition"] * AU_METERS
    if cleaned.get("bodyXSpeed") is not None:
        body[VEL][0] = cleaned["bodyXSpeed"] * 1000
    if cleaned.get("bodyYSpeed") is not None:
        body[VEL][1] = cleaned["bodyYSpeed"] * 1000

    refVal = cleaned.get("bodyReference")
    engine.setBodyReference(selectedBody, int(refVal) if refVal not in (None, "") else -1)

    colour = (cleaned.get("bodyColour") or "").strip().lower()
    if colour in mcolors.CSS4_COLORS:
        body[COLOUR] = [colour, colour]

    _saveSimulationState(request, storedSim, engine)
    return JsonResponse({})
