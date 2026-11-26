from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from PlanetaryOrbitSimulator.planetarySimulationEngine import (
    AU_METERS,
    COLOUR,
    MASS,
    NAME,
    POS,
    RADIUS,
    SECONDS_PER_DAY,
    VEL,
    PlanetarySimulationEngine,
    getAvailableTemplates,
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
    "focusBody",
    "listOfBodies",
    "bodyPoints",
    "ticksPerStorageUpdate",
    "ticksPerPageUpdate",
    "secondsPerSimulationTick",
)


def _roundSigFigs(number, sigFigs):
    return float(f"{number:.{sigFigs}g}")


def _formatFormErrors(form):
    messages = []
    for field, errs in form.errors.items():
        prefix = "" if field == "__all__" else f"{field}: "
        messages.append(f"{prefix}{'; '.join(str(e) for e in errs)}")
    return " | ".join(messages) or "Invalid form data"


def _loadPreferencesIntoSession(request, user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    request.session["backgroundStyle"] = profile.backgroundStylePreference
    request.session["axisStyle"] = profile.axisStylePreference
    request.session["showExperimentalTemplates"] = profile.showExperimentalTemplates
    return profile


def _getStylePreferences(request):
    if "backgroundStyle" not in request.session or "axisStyle" not in request.session:
        _loadPreferencesIntoSession(request, request.user)
    return request.session["backgroundStyle"], request.session["axisStyle"]


def _getShowExperimentalTemplates(request):
    if "showExperimentalTemplates" not in request.session:
        _loadPreferencesIntoSession(request, request.user)
    return bool(request.session["showExperimentalTemplates"])


def _copySimulationFields(target, source):
    for field in SIMULATION_FIELDS:
        setattr(target, field, getattr(source, field))
    return target


def _imageCacheKey(user):
    return f"sim_image:{user.pk}"


def _renderAndCacheGraph(request, engine):
    bgStyle, axisStyle = _getStylePreferences(request)
    pngBytes = engine.renderGraphBytes(bgStyle, axisStyle)
    cache.set(_imageCacheKey(request.user), pngBytes, timeout=3600)
    return pngBytes


def _getActiveEngine(request):
    engine = request.session.get("simulationEngine")
    if engine is not None:
        return engine
    simId = request.session.get("selectedSimulationId")
    if simId is not None:
        storedSim = StoredSimulation.objects.filter(pk=simId, user=request.user).first()
        if storedSim is not None:
            engine = _copySimulationFields(PlanetarySimulationEngine(), storedSim)
            engine.simulationName = storedSim.name
            engine.updateFocusPoint()
            request.session["simulationEngine"] = engine
            return engine
    return None


def _persistEngineToDb(request, engine):
    simId = request.session.get("selectedSimulationId")
    storedSim = None
    if simId is not None:
        storedSim = StoredSimulation.objects.filter(pk=simId, user=request.user).first()
    if storedSim is None:
        storedSim = StoredSimulation(user=request.user)
    _copySimulationFields(storedSim, engine)
    storedSim.name = engine.simulationName or "Untitled Simulation"
    storedSim.save()
    request.session["selectedSimulationId"] = storedSim.pk
    return storedSim


def _saveSessionState(request, engine, saveToDb=False, drawGraph=True):
    if drawGraph:
        _renderAndCacheGraph(request, engine)
    request.session["simulationEngine"] = engine
    request.session.modified = True
    if saveToDb:
        _persistEngineToDb(request, engine)


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
    return SimulationNameForm(None, initial=initial, body_choices=bodyChoices)


def _stepSimulationEngine(engine, reverseSimulation=0, dontRunSimulation=0):
    if dontRunSimulation != 0:
        return "No"
    if reverseSimulation == 0:
        engine.runSimulation(engine.ticksPerPageUpdate + engine.simulationTime)
        return "No"
    if engine.simulationTime > 0:
        engine.rollbackSimulation()
    return "Yes"


def homePage(request):
    return render(request, "HomePage.html")


@login_required(login_url="/login/")
def simulationImage(request):
    pngBytes = cache.get(_imageCacheKey(request.user))
    if pngBytes is None:
        engine = _getActiveEngine(request)
        if engine is None:
            return HttpResponse(status=404)
        pngBytes = _renderAndCacheGraph(request, engine)
    response = HttpResponse(pngBytes, content_type="image/png")
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


@login_required(login_url="/login/")
def settingsPage(request):
    bgColours = [bg for _, bg, _ in GRAPH_STYLES]
    if request.method == "POST":
        try:
            styleIndex = int(request.POST.get("styleIndex", -1))
        except (TypeError, ValueError):
            styleIndex = -1
        if 0 <= styleIndex < len(GRAPH_STYLES):
            _, bg, axis = GRAPH_STYLES[styleIndex]
            request.session["backgroundStyle"] = bg
            request.session["axisStyle"] = axis
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.backgroundStylePreference = bg
            profile.axisStylePreference = axis
            profile.save()

        if "showExperimentalTemplates" in request.POST:
            rawVal = request.POST.get("showExperimentalTemplates", "").strip().lower()
            if rawVal in ("1", "true", "0", "false"):
                enabled = rawVal in ("1", "true")
                profile, _ = UserProfile.objects.get_or_create(user=request.user)
                profile.showExperimentalTemplates = enabled
                profile.save()
                request.session["showExperimentalTemplates"] = enabled

        return redirect("/settings/")

    bgStyle, _ = _getStylePreferences(request)
    styleIndex = bgColours.index(bgStyle) if bgStyle in bgColours else 0
    return render(request, "SettingsPage.html", {
        "graphStyles": [label for label, _, _ in GRAPH_STYLES],
        "styleIndex": styleIndex,
        "showExperimentalTemplates": _getShowExperimentalTemplates(request),
    })


def loginPage(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user is not None:
            login(request, user)
            _loadPreferencesIntoSession(request, user)
            return redirect("/")
        form.add_error(None, "Invalid username or password.")
    return render(request, "LoginPage.html", {"loginForm": form})


def registerPage(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        login(request, user)
        _loadPreferencesIntoSession(request, user)
        return redirect("/")
    return render(request, "RegisterPage.html", {"registerForm": form})


@login_required(login_url="/login/")
def createPage(request, templateIndex=0):
    showExperimental = _getShowExperimentalTemplates(request)
    availableTemplates = getAvailableTemplates(includeExperimental=showExperimental)
    availableIds = {tpl["id"] for tpl in availableTemplates}
    if availableTemplates and templateIndex not in availableIds:
        fallbackId = 0 if 0 in availableIds else availableTemplates[0]["id"]
        return redirect("/create/" if fallbackId == 0 else f"/create/{fallbackId}/")

    engine = PlanetarySimulationEngine()
    engine.loadTemplates(templateIndex)

    form = _buildSimulationForm(request, engine.simulationName, engine)
    request.session.pop("selectedSimulationId", None)
    _saveSessionState(request, engine, saveToDb=False, drawGraph=True)

    return render(request, "NewSystemPage.html", {
        "templatesList": availableTemplates,
        "templateIndex": templateIndex,
        "form": form,
    })


@login_required(login_url="/login/")
def loadingPage(request, saveIndex=0):
    allSimulations = list(StoredSimulation.objects.filter(user=request.user).order_by("pk"))
    if not allSimulations or not (0 <= saveIndex < len(allSimulations)):
        return redirect("/")

    selectedSimulation = allSimulations[saveIndex]
    request.session["selectedSimulationId"] = selectedSimulation.pk

    engine = _copySimulationFields(PlanetarySimulationEngine(), selectedSimulation)
    engine.simulationName = selectedSimulation.name
    engine.updateFocusPoint()
    infoForm = _buildSimulationForm(request, selectedSimulation.name, engine)

    _saveSessionState(request, engine, saveToDb=False, drawGraph=True)

    return render(request, "LoadSystemPage.html", {
        "allSimulations": allSimulations,
        "saveIndex": saveIndex,
        "name": selectedSimulation.name,
        "infoForm": infoForm,
        **_getDisplayMetrics(engine),
    })


@login_required(login_url="/login/")
def editSimulationPage(request, selectedBody=0):
    engine = _getActiveEngine(request)
    if engine is None:
        return redirect("/create/")

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

    detailsForm = BodyDetailsForm(initial=bodyDetails, body_choices=bodyChoices)
    _saveSessionState(request, engine, saveToDb=False, drawGraph=True)

    return render(request, "editSystemPage.html", {
        **_getDisplayMetrics(engine),
        "selectedBody": selectedBody,
        "nextBody": min(selectedBody + 1, numBodies),
        "lastBody": max(selectedBody - 1, 0),
        "detailsForm": detailsForm,
        "simulationName": engine.simulationName,
        "focusBodyName": engine.focusBodyName,
    })


@login_required(login_url="/login/")
def runSimulation(request, dontRunSimulation=0, reverseSimulation=0):
    engine = _getActiveEngine(request)
    if engine is None:
        return redirect("/create/")

    isReverse = _stepSimulationEngine(engine, reverseSimulation, dontRunSimulation)
    isNewSave = request.session.get("selectedSimulationId") is None
    _saveSessionState(request, engine, saveToDb=isNewSave, drawGraph=True)
    infoForm = _buildSimulationForm(request, engine.simulationName, engine, includeFocusBody=True)

    return render(request, "RunSimulationPage.html", {
        **_getDisplayMetrics(engine),
        "isSimulationInReverse": isReverse,
        "simulationName": engine.simulationName,
        "focusBodyName": engine.focusBodyName,
        "infoForm": infoForm,
    })


@login_required(login_url="/login/")
@require_POST
def updateSimulationImage(request, reverseSimulation=0):
    engine = _getActiveEngine(request)
    if engine is None:
        return JsonResponse({"error": "No active simulation"}, status=400)

    isReverse = _stepSimulationEngine(engine, reverseSimulation=reverseSimulation, dontRunSimulation=0)
    _saveSessionState(request, engine, saveToDb=False, drawGraph=True)

    return JsonResponse({
        "daysElapsed": _getDisplayMetrics(engine)["daysElapsed"],
        "isSimulationInReverse": isReverse,
        "focusBody": engine.focusBody,
        "focusBodyName": engine.focusBodyName,
        "focusChoices": _getBodyChoices(engine),
    })


@login_required(login_url="/login/")
@require_POST
def saveSimulation(request):
    engine = _getActiveEngine(request)
    if engine is None:
        return JsonResponse({"error": "No active simulation"}, status=400)

    _saveSessionState(request, engine, saveToDb=True, drawGraph=False)
    return JsonResponse({"saved": True})


@login_required(login_url="/login/")
@require_POST
def changeSimulationFocus(request):
    engine = _getActiveEngine(request)
    if engine is None:
        return JsonResponse({"error": "No active simulation"}, status=400)

    engine.focusBody += 1
    engine.updateFocusPoint()
    _saveSessionState(request, engine, saveToDb=False, drawGraph=True)

    relativeBodyName = (
        engine.getBodyReferenceName(engine.focusBody)
        if engine.focusBody != -1 else "None (Static Grid)"
    )
    return JsonResponse({
        "focusBody": engine.focusBody,
        "focusBodyName": engine.focusBodyName,
        "relativeBodyName": relativeBodyName,
    })


@login_required(login_url="/login/")
@require_POST
def processRunForm(request, isCreating=0):
    engine = _getActiveEngine(request)
    if engine is None:
        return JsonResponse({"error": "No active simulation"}, status=400)

    runForm = SimulationNameForm(request.POST, body_choices=_getBodyChoices(engine))
    if not runForm.is_valid():
        return JsonResponse({"error": _formatFormErrors(runForm)}, status=400)

    cleaned = runForm.cleaned_data
    if cleaned.get("simulationName"):
        engine.simulationName = cleaned["simulationName"]
    if cleaned.get("simulationSize") is not None:
        engine.simulationSize = cleaned["simulationSize"]
    if cleaned.get("simulationTimePerUpdate") is not None and engine.secondsPerSimulationTick > 0:
        adjustedSeconds = round(cleaned["simulationTimePerUpdate"] * SECONDS_PER_DAY)
        engine.ticksPerPageUpdate = max(1, round(adjustedSeconds / engine.secondsPerSimulationTick))

    focusedBodyVal = cleaned.get("focusedBody")
    if focusedBodyVal not in (None, ""):
        engine.focusBody = int(focusedBodyVal)
        engine.updateFocusPoint()

    _saveSessionState(request, engine, saveToDb=(isCreating == 0), drawGraph=True)
    metrics = _getDisplayMetrics(engine)

    return JsonResponse({
        "simulationName": engine.simulationName,
        "daysPerTick": metrics["daysPerTick"],
        "simulationSizeAU": metrics["simulationSizeAU"],
        "simulationSizeKM": metrics["simulationSizeKM"],
        "focusBody": engine.focusBody,
        "focusBodyName": engine.focusBodyName,
    })


@login_required(login_url="/login/")
@require_POST
def processEditForm(request, selectedBody):
    engine = _getActiveEngine(request)
    if engine is None:
        return JsonResponse({"error": "No active simulation"}, status=400)

    if selectedBody < 0 or selectedBody > len(engine.listOfBodies):
        return JsonResponse({"error": "Body index out of range"}, status=400)

    bodyChoices = _getBodyChoices(engine, "None (Static Grid)", excludeIndex=selectedBody)
    detailsForm = BodyDetailsForm(request.POST, body_choices=bodyChoices)
    if not detailsForm.is_valid():
        return JsonResponse({"error": _formatFormErrors(detailsForm)}, status=400)

    cleaned = detailsForm.cleaned_data
    if selectedBody == len(engine.listOfBodies):
        engine.addBody([[0, 0, 0], [0, 0, 0], 0, 0, ["white", "white"], "", -1])
        engine.focusBody = selectedBody

    body = engine.listOfBodies[selectedBody]
    if cleaned.get("bodyMass") is not None:
        body[MASS] = cleaned["bodyMass"]
    if cleaned.get("bodyRadius") is not None:
        body[RADIUS] = cleaned["bodyRadius"] * 1000
    bodyName = (cleaned.get("bodyName") or "").strip()
    if bodyName:
        body[NAME] = bodyName
    if cleaned.get("bodyXPosition") is not None:
        body[POS][0] = cleaned["bodyXPosition"] * AU_METERS
    if cleaned.get("bodyYPosition") is not None:
        body[POS][1] = cleaned["bodyYPosition"] * AU_METERS
    if cleaned.get("bodyXSpeed") is not None:
        body[VEL][0] = cleaned["bodyXSpeed"] * 1000
    if cleaned.get("bodyYSpeed") is not None:
        body[VEL][1] = cleaned["bodyYSpeed"] * 1000

    if "bodyReference" in request.POST:
        refVal = cleaned.get("bodyReference")
        engine.setBodyReference(selectedBody, int(refVal) if refVal not in (None, "") else -1)

    colour = cleaned.get("bodyColour")
    if colour:
        body[COLOUR] = [colour, colour]

    engine.invalidatePairCache()
    engine.updateFocusPoint()
    _saveSessionState(request, engine, saveToDb=True, drawGraph=True)
    return JsonResponse({
        "bodyIndex": selectedBody,
        "numBodies": len(engine.listOfBodies),
        "focusBodyName": engine.focusBodyName,
    })
