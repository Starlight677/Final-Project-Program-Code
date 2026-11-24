import io
import math

import matplotlib
matplotlib.use("agg")  # Headless backend for Django worker threads
matplotlib.rcParams["path.simplify"] = True
matplotlib.rcParams["path.simplify_threshold"] = 0.2
matplotlib.rcParams["agg.path.chunksize"] = 10000

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np

G = 6.6743e-11
AU_METERS = 1.495979e11
SOLAR_MASS = 1.989e30
EARTH_MASS = 5.972e24
MOON_MASS = EARTH_MASS * 0.0123
SECONDS_PER_DAY = 86400
SIGNIFICANCE_THRESHOLD = 1e-6
MAX_HISTORY_POINTS = 5000
NUMPY_BODY_THRESHOLD = 12

# Indices into each body entry: [pos, vel, mass, radius, [line_colour, marker_colour], name, ref_index]
POS, VEL, MASS, RADIUS, COLOUR, NAME, REF = range(7)


def _makeBody(pos, vel, mass, radius, colour, name, ref=-1):
    return [list(pos), list(vel), mass, radius, [colour, colour], name, ref]


SYSTEM_TEMPLATES = {
    0: {
        "name": "Inner Solar System",
        "size": 2,
        "dt": 60,
        "storageSeconds": 3600 * 12,
        "pageSeconds": SECONDS_PER_DAY * 5,
        "bodies": (
            ((0, 0, 0), (0, 0, 0), SOLAR_MASS * 1, 7e8, "yellow", "The Sun", -1),
            ((0, -6.982e10, 0), (-38900, 0, 0), EARTH_MASS * 0.055, 2.439e6, "darkgrey", "Mercury", 0),
            ((1.082e11, 0, 0), (0, -35000, 0), EARTH_MASS * 0.815, 6.05e6, "orange", "Venus", 0),
            ((-1.521e11, 0, 0), (0, 29290, 0), EARTH_MASS * 1, 6.3e6, "blue", "The Earth", 0),
            ((-1.521e11, 3.84e8, 0), (1022, 29290, 0), MOON_MASS * 1, 1.738e6, "silver", "The Moon", 3),
            ((0, 2.064e11, 0), (26490, 0, 0), EARTH_MASS * 0.107, 3.396e6, "red", "Mars", 0),
        ),
    },
    1: {
        "name": "Galilean Moons of Jupiter",
        "size": 0.02,
        "dt": 6,
        "storageSeconds": 3600,
        "pageSeconds": SECONDS_PER_DAY / 4,
        "bodies": (
            ((0, 0, 0), (0, 0, 0), EARTH_MASS * 318, 6.989e7, "darkorange", "Jupiter", -1),
            ((4.217e8, 0, 0), (0, -17334, 0), MOON_MASS * 1.05, 3.643e6, "gold", "Io", 0),
            ((-6.71e8, 0, 0), (0, 13703, 0), MOON_MASS * 0.9, 3.122e6, "lightsteelblue", "Europa", 0),
            ((0, 1.07e9, 0), (10880, 0, 0), MOON_MASS * 2, 5.262e6, "silver", "Ganymede", 0),
            ((0, -1.883e9, 0), (-8204, 0, 0), MOON_MASS * 1.5, 4.821e6, "grey", "Callisto", 0),
        ),
    },
    2: {
        "name": "Ascendia Primary Star",
        "size": 0.5,
        "dt": 60,
        "storageSeconds": 3600 * 3,
        "pageSeconds": SECONDS_PER_DAY / 2,
        "bodies": (
            ((0, 0, 0), (0, 0, 0), SOLAR_MASS * 0.2656, 7e7 * 0.474, "orange", "Col 285 Sector ZX-R b5-0 A", -1),
            ((-3.3e9, 0, 0), (0, 103364, 0), EARTH_MASS * 0.0908, 2.887e6, "grey", "Col 285 Sector ZX-R b5-0 A 1", 0),
            ((6e9, 0, 0), (0, -76657, 0), EARTH_MASS * 0.1077, 3.049e6, "darkgrey", "Stephenson's Rock", 0),
            ((0, -1.04e10, 0), (-58225, 0, 0), EARTH_MASS * 0.0965, 2.944e6, "orangered", "Col 285 Sector ZX-R b5-0 A 3", 0),
            ((0, 1.9e10, 0), (43077, 0, 0), EARTH_MASS * 0.1623, 4.434e6, "lightskyblue", "Ascendia", 0),
            ((0, -3.5e10, 0), (-31739, 0, 0), EARTH_MASS * 0.3876, 5.802e6, "silver", "Col 285 Sector ZX-R b5-0 A 5", 0),
            ((-6.44e10, 0, 0), (0, 23398, 0), EARTH_MASS * 0.2808, 5.27e6, "silver", "Col 285 Sector ZX-R b5-0 A 6", 0),
        ),
    },
    3: {
        "name": "Binary Stars",
        "size": 2,
        "dt": 60,
        "storageSeconds": 3600 * 12,
        "pageSeconds": SECONDS_PER_DAY * 30,
        "bodies": (
            ((-7.51e10, 0, 0), (0, 11000, 0), SOLAR_MASS * 1, 7e7, "yellow", "Primary Star", -1),
            ((1.521e11, 0, 0), (0, -22000, 0), SOLAR_MASS * 0.5, 5e7, "orange", "Secondary Star", -1),
        ),
    },
    4: {
        "name": "Single Star",
        "size": 1,
        "dt": 60,
        "storageSeconds": 3600 * 12,
        "pageSeconds": SECONDS_PER_DAY * 5,
        "bodies": (
            ((0, 0, 0), (0, 0, 0), SOLAR_MASS * 1, 7e7, "yellow", "Primary Star", -1),
        ),
    },
    5: {
        "name": "Madman's Halo",
        "size": 11,
        "dt": 1800,
        "storageSeconds": 7200,
        "pageSeconds": SECONDS_PER_DAY * 30,
        "bodies": (
            ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), SOLAR_MASS * 1.320313, 7e7 * 1.2902, "white", "Pyroifoi RD-Z d1-223", -1),
            ((-3300000000.0, 0.0, 0.0), (0.0, 230543.0, 0.0), EARTH_MASS * 15.172054, 1.27e7, "saddlebrown", "Pyroifoi RD-Z d1-223 1", 0),
            ((5700000000.0, 0.0, 0.0), (0.0, -175417.0, 0.0), EARTH_MASS * 5.797106, 1.00e7, "maroon", "Pyroifoi RD-Z d1-223 2", 0),
            ((0.0, -399010000000.0, 0.0), (20968.0, 0.0, 0.0), EARTH_MASS * 1342.156738, 7.60e7, "mediumblue", "Pyroifoi RD-Z d1-223 3", 0),
            ((643399138.1, -399010000000.0, 0.0), (20968.0, 28835.3, 0.0), EARTH_MASS * 0.011476, 1.57e6, "gold", "Pyroifoi RD-Z d1-223 3 a", 3),
            ((1044040809.0, -399010000000.0, 0.0), (20968.0, 23063.4, 0.0), EARTH_MASS * 0.010893, 1.55e6, "silver", "Pyroifoi RD-Z d1-223 3 b", 3),
            ((1051164498.5, -399010000000.0, 0.0), (20968.0, 22018.8, 0.0), EARTH_MASS * 0.008608, 1.43e6, "sandybrown", "Pyroifoi RD-Z d1-223 3 c", 3),
            ((0.0, -408850000000.0, 0.0), (13591.0, 0.0, 0.0), EARTH_MASS * 1.773461, 7.20e6, "deepskyblue", "Madman's Halo", 0),
            ((0.0, -408700401992.1, 0.0), (11417.2, 0.0, 0.0), EARTH_MASS * 0.000172, 3.93e5, "silver", "Pyroifoi RD-Z d1-223 4 a", 7),
            ((-583690000000.0, 0.0, 0.0), (0.0, -17475.0, 0.0), EARTH_MASS * 1308.151978, 7.59e7, "mediumblue", "Pyroifoi RD-Z d1-223 5", 0),
            ((-582865087111.6, 0.0, 0.0), (0.0, 7666.3, 0.0), EARTH_MASS * 0.004294, 1.14e6, "silver", "Pyroifoi RD-Z d1-223 5 a", 9),
            ((-583690000000.0, 1070105762.3, 0.0), (-22073.9, -17475.0, 0.0), EARTH_MASS * 0.001776, 8.51e5, "silver", "Pyroifoi RD-Z d1-223 5 b", 9),
            ((-585759554317.0, 0.0, 0.0), (-0.0, -33347.8, 0.0), EARTH_MASS * 0.006879, 1.33e6, "sandybrown", "Pyroifoi RD-Z d1-223 5 c", 9),
            ((-583690000000.0, -2694282701.8, 0.0), (13911.4, -17475.0, 0.0), EARTH_MASS * 0.006498, 1.31e6, "silver", "Pyroifoi RD-Z d1-223 5 d", 9),
            ((-596630000000.0, 0.0, 0.0), (0.0, -11052.0, 0.0), EARTH_MASS * 31.564976, 3.41e7, "whitesmoke", "Pyroifoi RD-Z d1-223 6", 0),
            ((-596411065182.7, 0.0, 0.0), (0.0, -3471.3, 0.0), EARTH_MASS * 0.00018, 3.98e5, "gold", "Pyroifoi RD-Z d1-223 6 a", 14),
            ((0.0, 950720000000.0, 0.0), (-13675.0, 0.0, 0.0), SOLAR_MASS * 0.011719, 7e7 * 0.0603, "darkmagenta", "Pyroifoi RD-Z d1-223 7", 0),
            ((1937555573.4, 950720000000.0, 0.0), (-13675.0, 28336.0, 0.0), EARTH_MASS * 0.006953, 1.33e6, "silver", "Pyroifoi RD-Z d1-223 7 a", 16),
            ((0.0, 953432368185.1, 0.0), (-37624.2, 0.0, 0.0), EARTH_MASS * 0.006178, 1.28e6, "silver", "Pyroifoi RD-Z d1-223 7 b", 16),
            ((-3458488009.2, 950720000000.0, 0.0), (-13675.0, -21209.1, 0.0), EARTH_MASS * 0.005175, 1.21e6, "sandybrown", "Pyroifoi RD-Z d1-223 7 c", 16),
            ((-0.0, 945995000660.1, 0.0), (4470.3, -0.0, 0.0), EARTH_MASS * 0.004555, 1.16e6, "silver", "Pyroifoi RD-Z d1-223 7 d", 16),
            ((4509413714.8, 955229413714.8, 0.0), (-24719.2, 11044.2, 0.0), EARTH_MASS * 0.003913, 1.10e6, "silver", "Pyroifoi RD-Z d1-223 7 e", 16),
            ((-6672850099.7, 957392850099.7, 0.0), (-22754.0, -9079.0, 0.0), EARTH_MASS * 0.02264, 1.96e6, "silver", "Pyroifoi RD-Z d1-223 7 f", 16),
            ((0.0, 997120000000.0, 0.0), (-7836.0, 0.0, 0.0), EARTH_MASS * 69.959572, 4.04e7, "peru", "Pyroifoi RD-Z d1-223 8", 0),
            ((1403700000000.0, 0.0, 0.0), (0.0, 11209.0, 0.0), EARTH_MASS * 2188.751709, 7.08e7, "mediumblue", "Pyroifoi RD-Z d1-223 9", 0),
            ((1404319433363.4, 0.0, 0.0), (0.0, 48737.7, 0.0), EARTH_MASS * 0.16297, 3.48e6, "lightsteelblue", "Pyroifoi RD-Z d1-223 9 a", 24),
            ((1403700000000.0, 1106238462.6, 0.0), (-28082.6, 11209.0, 0.0), EARTH_MASS * 0.202102, 3.73e6, "sandybrown", "Pyroifoi RD-Z d1-223 9 b", 24),
            ((1401586677626.1, 0.0, 0.0), (-0.0, -9108.9, 0.0), EARTH_MASS * 0.787346, 5.67e6, "orangered", "Pyroifoi RD-Z d1-223 9 c", 24),
            ((1403700000000.0, -4934228254.2, 0.0), (13296.9, 11209.0, 0.0), EARTH_MASS * 12.583962, 3.20e7, "peru", "Pyroifoi RD-Z d1-223 9 d", 24),
            ((1409717486834.0, 6017486834.0, 0.0), (-7159.5, 18368.5, 0.0), EARTH_MASS * 42.22065, 4.55e7, "whitesmoke", "Pyroifoi RD-Z d1-223 9 e", 24),
            ((1409977787956.3, 6017486834.0, 0.0), (-7159.5, 26409.0, 0.0), EARTH_MASS * 0.03382, 2.82e6, "snow", "Pyroifoi RD-Z d1-223 9 e a", 29),
            ((1460000000000.0, 0.0, 0.0), (0.0, 7253.0, 0.0), EARTH_MASS * 20.416899, 1.76e7, "snow", "Pyroifoi RD-Z d1-223 10", 0),
        ),
    },
}

TEMPLATE_NAMES = [SYSTEM_TEMPLATES[i]["name"] for i in range(len(SYSTEM_TEMPLATES))]


class PlanetarySimulationEngine:
    """N-body gravitational simulator with adaptive pair filtering, NumPy vectorization, and orbital trail rendering."""

    def __init__(self):
        self.listOfBodies = []
        self.simulationTime = 0
        self.simulationSize = 0
        self.focusPoint = [0, 0]
        self.focusBody = -1
        self.focusBodyName = "None"
        self.bodyPoints = []
        self.ticksPerStorageUpdate = 0
        self.ticksPerPageUpdate = 0
        self.secondsPerSimulationTick = 0
        self.simulationName = ""
        self._significantCompanions = None
        self._activePairs = None

    def invalidatePairCache(self):
        """Clear cached pair significance structures after body list or history changes."""
        self._significantCompanions = None
        self._activePairs = None

    def getBodyReference(self, bodyIndex):
        """Return the reference body index for bodyIndex, or -1 for static grid."""
        if bodyIndex < 0 or bodyIndex >= len(self.listOfBodies):
            return -1
        body = self.listOfBodies[bodyIndex]
        if len(body) <= REF or isinstance(body[REF], bool) or not isinstance(body[REF], int):
            return -1
        ref = body[REF]
        if ref < 0 or ref >= len(self.listOfBodies) or ref == bodyIndex:
            return -1
        return ref

    def getBodyReferenceName(self, bodyIndex):
        """Return the display name of the reference body for bodyIndex."""
        ref = self.getBodyReference(bodyIndex)
        if ref == -1:
            return "None (Static Grid)"
        return self.listOfBodies[ref][NAME]

    def setBodyReference(self, bodyIndex, refIndex):
        """Set the reference body index for bodyIndex, falling back to -1 if invalid."""
        if bodyIndex < 0 or bodyIndex >= len(self.listOfBodies):
            return
        if (
            isinstance(refIndex, bool)
            or not isinstance(refIndex, int)
            or refIndex < 0
            or refIndex >= len(self.listOfBodies)
            or refIndex == bodyIndex
        ):
            refIndex = -1
        body = self.listOfBodies[bodyIndex]
        if len(body) > REF:
            body[REF] = refIndex
        else:
            body.append(refIndex)

    def _findCollidingPair(self):
        """Return the first pair of overlapping body indices, or None if no bodies overlap."""
        bodies = self.listOfBodies
        n = len(bodies)
        for i in range(n):
            pos1 = bodies[i][POS]
            r1 = bodies[i][RADIUS]
            for j in range(i + 1, n):
                pos2 = bodies[j][POS]
                dx = pos1[0] - pos2[0]
                dy = pos1[1] - pos2[1]
                dz = pos1[2] - pos2[2]
                radSum = r1 + bodies[j][RADIUS]
                if dx * dx + dy * dy + dz * dz <= radSum * radSum:
                    return i, j
        return None

    def _resolveCollisions(self):
        """Resolve all currently overlapping body pairs before forces are applied."""
        merged = False
        while True:
            pair = self._findCollidingPair()
            if pair is None:
                break
            i, j = pair
            self.mergeCollidingBodies(i, j)
            print(f"Body Collision resolved between body {i} and body {j}.")
            merged = True
        return merged

    def _applyPairGravity(self, body1, body2, filterTick):
        """Apply mutual gravitational impulse to body1 and body2 and return significance."""
        pos1, pos2 = body1[POS], body2[POS]
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        dz = pos1[2] - pos2[2]
        distSq = dx * dx + dy * dy + dz * dz
        if distSq <= 0.0:
            return False

        dist = math.sqrt(distSq)
        invDistCubed = G / (distSq * dist)
        mod1 = abs(body2[MASS] * invDistCubed)
        mod2 = abs(body1[MASS] * invDistCubed)

        a1x, a1y, a1z = -dx * mod1, -dy * mod1, -dz * mod1
        a2x, a2y, a2z = dx * mod2, dy * mod2, dz * mod2

        exceedsThreshold = (
            (abs(a1x) + abs(a1y) + abs(a1z)) >= SIGNIFICANCE_THRESHOLD
            or (abs(a2x) + abs(a2y) + abs(a2z)) >= SIGNIFICANCE_THRESHOLD
        )

        # Batch below-threshold pairs over the full storage interval on filter ticks
        dt = self.secondsPerSimulationTick
        if filterTick and not exceedsThreshold and self.ticksPerStorageUpdate > 1:
            dt *= self.ticksPerStorageUpdate

        vel1, vel2 = body1[VEL], body2[VEL]
        vel1[0] += a1x * dt
        vel1[1] += a1y * dt
        vel1[2] += a1z * dt
        vel2[0] += a2x * dt
        vel2[1] += a2y * dt
        vel2[2] += a2z * dt
        return exceedsThreshold

    def mergeCollidingBodies(self, body1Index, body2Index):
        """Merge two colliding bodies into the lower-indexed slot and remap tracking structures."""
        if body1Index > body2Index:
            body1Index, body2Index = body2Index, body1Index

        body1 = self.listOfBodies[body1Index]
        body2 = self.listOfBodies[body2Index]
        m1, m2 = body1[MASS], body2[MASS]
        totalMass = m1 + m2

        if totalMass > 0:
            mergedCoords = [(m1 * body1[POS][i] + m2 * body2[POS][i]) / totalMass for i in range(3)]
            mergedMotion = [(m1 * body1[VEL][i] + m2 * body2[VEL][i]) / totalMass for i in range(3)]
        else:
            mergedCoords = [(body1[POS][i] + body2[POS][i]) / 2 for i in range(3)]
            mergedMotion = [(body1[VEL][i] + body2[VEL][i]) / 2 for i in range(3)]

        mergedRadius = (body1[RADIUS] ** 3 + body2[RADIUS] ** 3) ** (1 / 3)
        dominant = body1 if m1 >= m2 else body2
        mergedColour = dominant[COLOUR][0] if isinstance(dominant[COLOUR], list) else dominant[COLOUR]
        mergedName = dominant[NAME]
        rawRef = dominant[REF] if len(dominant) > REF else -1
        mergedRef = rawRef if isinstance(rawRef, int) and not isinstance(rawRef, bool) else -1
        if mergedRef in (body1Index, body2Index):
            mergedRef = -1

        self.listOfBodies[body1Index] = _makeBody(
            mergedCoords, mergedMotion, totalMass, mergedRadius, mergedColour, mergedName, mergedRef
        )
        self.listOfBodies.pop(body2Index)
        self.bodyPoints.pop(body2Index)

        if self.focusBody == body2Index:
            self.focusBody = -1
            self.focusBodyName = "None"
        else:
            if self.focusBody > body2Index:
                self.focusBody -= 1
            if self.focusBody == body1Index:
                self.focusBodyName = mergedName

        for body in self.listOfBodies:
            if len(body) > REF and isinstance(body[REF], int) and not isinstance(body[REF], bool):
                if body[REF] == body2Index:
                    body[REF] = -1
                elif body[REF] > body2Index:
                    body[REF] -= 1

        self.invalidatePairCache()

    def renderGraphBytes(self, backgroundColour="black", graphColour="white"):
        """Render the current orbital state and trails to PNG bytes using OO Matplotlib."""
        self.updateFocusPoint()

        fig = Figure(figsize=(6.9, 6.9))
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        fig.set_facecolor(backgroundColour)
        ax.set_facecolor(backgroundColour)
        ax.set_aspect("equal", adjustable="box")

        for spine in ax.spines.values():
            spine.set_color(graphColour)
        ax.tick_params(axis="both", colors=graphColour)
        ax.xaxis.label.set_color(graphColour)
        ax.yaxis.label.set_color(graphColour)

        viewBounds = (
            -self.simulationSize + self.focusPoint[0],
            self.simulationSize + self.focusPoint[0],
            -self.simulationSize + self.focusPoint[1],
            self.simulationSize + self.focusPoint[1],
        )
        pixelSizeAU = (2.0 * self.simulationSize) / 550.0 if self.simulationSize > 0 else 0.0

        ax.set_xlim(viewBounds[0], viewBounds[1])
        ax.set_ylim(viewBounds[2], viewBounds[3])
        ax.set_xlabel("Distance (AU)")
        ax.set_ylabel("Distance (AU)")
        ax.grid(True)

        refSliceCache = {}
        for bodyIndex in range(len(self.listOfBodies) - 1, -1, -1):
            try:
                self.plotBodyPoints(
                    ax,
                    self.listOfBodies[bodyIndex],
                    bodyIndex,
                    viewBounds,
                    pixelSizeAU,
                    refSliceCache=refSliceCache,
                )
            except IndexError:
                continue

        buf = io.BytesIO()
        fig.savefig(buf, format="png", pil_kwargs={"compress_level": 1})
        return buf.getvalue()

    def _smoothOrbitPoints(self, x, y, targetPoints=120):
        """Vectorized centripetal Catmull-Rom spline interpolation for sparse orbital arcs."""
        n = x.size
        if n < 4 or n >= targetPoints:
            return x, y

        subdivisions = max(2, min(8, int(math.ceil(targetPoints / max(1, n - 1)))))

        # Second-order quadratic extrapolation for phantom boundary control points
        ptsExt = np.empty((n + 2, 2), dtype=float)
        ptsExt[1:-1, 0] = x
        ptsExt[1:-1, 1] = y
        ptsExt[0] = 3.0 * ptsExt[1] - 3.0 * ptsExt[2] + ptsExt[3]
        ptsExt[-1] = 3.0 * ptsExt[-2] - 3.0 * ptsExt[-3] + ptsExt[-4]

        # Centripetal knot spacing (alpha = 0.5) prevents cusps on uneven end steps
        diffs = np.diff(ptsExt, axis=0)
        dt = np.sqrt(np.maximum(np.hypot(diffs[:, 0], diffs[:, 1]), 1e-12))
        t = np.zeros(n + 2, dtype=float)
        t[1:] = np.cumsum(dt)

        t0, t1, t2, t3 = t[:-3, None], t[1:-2, None], t[2:-1, None], t[3:, None]
        frac = np.linspace(0.0, 1.0, subdivisions, endpoint=False)[None, :]
        ti = t1 + frac * (t2 - t1)

        w10 = ((ti - t0) / np.maximum(t1 - t0, 1e-12))[..., None]
        w21 = ((ti - t1) / np.maximum(t2 - t1, 1e-12))[..., None]
        w32 = ((ti - t2) / np.maximum(t3 - t2, 1e-12))[..., None]
        w20 = ((ti - t0) / np.maximum(t2 - t0, 1e-12))[..., None]
        w31 = ((ti - t1) / np.maximum(t3 - t1, 1e-12))[..., None]

        p0, p1, p2, p3 = ptsExt[:-3, None, :], ptsExt[1:-2, None, :], ptsExt[2:-1, None, :], ptsExt[3:, None, :]
        a1 = (1.0 - w10) * p0 + w10 * p1
        a2 = (1.0 - w21) * p1 + w21 * p2
        a3 = (1.0 - w32) * p2 + w32 * p3
        b1 = (1.0 - w20) * a1 + w20 * a2
        b2 = (1.0 - w31) * a2 + w31 * a3
        c = (1.0 - w21) * b1 + w21 * b2

        return np.append(c[..., 0].ravel(), x[-1]), np.append(c[..., 1].ravel(), y[-1])

    @staticmethod
    def _cumulativeBackwardAngles(dx, dy):
        """Return backward cumulative swept angles and indices crossing 2*pi radians."""
        cross = dx[:-1] * dy[1:] - dy[:-1] * dx[1:]
        dot = dx[:-1] * dx[1:] + dy[:-1] * dy[1:]
        cumTheta = np.abs(np.cumsum(np.arctan2(cross, dot)[::-1]))
        return cumTheta, np.flatnonzero(cumTheta >= 2.0 * np.pi)

    @staticmethod
    def _isTrailVisible(dx, dy, originX, originY, viewBounds, pixelSizeAU, marginRatio=0.05):
        """Return True if a trajectory spans at least one pixel and intersects the viewport."""
        xMin, xMax = float(dx.min()), float(dx.max())
        yMin, yMax = float(dy.min()), float(dy.max())
        xSpan = xMax - xMin
        ySpan = yMax - yMin
        if pixelSizeAU > 0.0 and xSpan < pixelSizeAU and ySpan < pixelSizeAU:
            return False
        if viewBounds is not None:
            minViewX, maxViewX, minViewY, maxViewY = viewBounds
            marginX = marginRatio * xSpan
            marginY = marginRatio * ySpan
            if (
                originX + xMax + marginX < minViewX
                or originX + xMin - marginX > maxViewX
                or originY + yMax + marginY < minViewY
                or originY + yMin - marginY > maxViewY
            ):
                return False
        return True

    @staticmethod
    def _trimToSingleRevolution(dx, dy, cumTheta, revIdx):
        """Trim (dx, dy) at the interpolated point where backward-swept angle reaches 2*pi."""
        segStart = (dx.size - 2) - revIdx
        segEnd = segStart + 1
        prevTheta = float(cumTheta[revIdx - 1]) if revIdx > 0 else 0.0
        currTheta = float(cumTheta[revIdx])
        alpha = (2.0 * np.pi - prevTheta) / max(currTheta - prevTheta, 1e-12)
        alpha = float(np.clip(alpha, 0.0, 1.0))

        startX = dx[segEnd] + alpha * (dx[segStart] - dx[segEnd])
        startY = dy[segEnd] + alpha * (dy[segStart] - dy[segEnd])
        return np.concatenate(([startX], dx[segEnd:])), np.concatenate(([startY], dy[segEnd:]))

    @staticmethod
    def _sliceTrailWindow(
        trailX,
        trailY,
        startIdx,
        totalLen,
        stride,
        bodyOffset=0,
        refXPoints=None,
        refYPoints=None,
        refOffset=0,
        refIdx=-1,
        refSliceCache=None,
    ):
        """Slice tail-aligned (trailX, trailY) and subtract cached reference slices when provided."""
        bStart = bodyOffset + startIdx
        bEnd = bodyOffset + totalLen
        tx = np.asarray(trailX[bStart:bEnd:stride], dtype=float)
        ty = np.asarray(trailY[bStart:bEnd:stride], dtype=float)
        if refXPoints is None or refYPoints is None:
            return tx, ty

        rStart = refOffset + startIdx
        rEnd = refOffset + totalLen
        cacheKey = (refIdx, rStart, rEnd, stride)
        if refSliceCache is not None and cacheKey in refSliceCache:
            rx, ry = refSliceCache[cacheKey]
        else:
            rx = np.asarray(refXPoints[rStart:rEnd:stride], dtype=float)
            ry = np.asarray(refYPoints[rStart:rEnd:stride], dtype=float)
            if refSliceCache is not None:
                refSliceCache[cacheKey] = (rx, ry)
        return tx - rx, ty - ry

    def _extractOrbitTrail(
        self,
        trailX,
        trailY,
        currentX,
        currentY,
        refXPoints=None,
        refYPoints=None,
        refCurrentX=0.0,
        refCurrentY=0.0,
        viewBounds=None,
        pixelSizeAU=0.0,
        refIdx=-1,
        refSliceCache=None,
    ):
        """
        Extract a single-revolution orbital trail in world coordinates in O(1) time
        using tail-aligned history windows and early viewport/sub-pixel culling.
        """
        useRelative = refXPoints is not None and refYPoints is not None
        totalLen = min(len(trailX), len(refXPoints)) if useRelative else len(trailX)
        if totalLen == 0:
            return None, None

        bodyOffset = len(trailX) - totalLen
        refOffset = (len(refXPoints) - totalLen) if useRelative else 0

        currDX = (currentX - refCurrentX) if useRelative else currentX
        currDY = (currentY - refCurrentY) if useRelative else currentY
        originX = refCurrentX if useRelative else 0.0
        originY = refCurrentY if useRelative else 0.0

        dx = dy = cumTheta = revHits = None
        winSize = min(128, totalLen)
        visitedTotal = False

        while True:
            if winSize >= totalLen:
                winSize = totalLen
                visitedTotal = True

            stride = max(1, winSize // 1500)
            stepsBack = (winSize - 1) // stride
            startIdx = max(0, (totalLen - 1) - stepsBack * stride)

            dx, dy = self._sliceTrailWindow(
                trailX,
                trailY,
                startIdx,
                totalLen,
                stride,
                bodyOffset=bodyOffset,
                refXPoints=refXPoints if useRelative else None,
                refYPoints=refYPoints if useRelative else None,
                refOffset=refOffset,
                refIdx=refIdx,
                refSliceCache=refSliceCache,
            )
            dx = np.append(dx, currDX)
            dy = np.append(dy, currDY)

            if dx.size > 1:
                stepSq = np.diff(dx) ** 2 + np.diff(dy) ** 2
                keep = np.concatenate(([True], stepSq > 1e-24))
                dx, dy = dx[keep], dy[keep]

            if dx.size >= 2:
                cumTheta, revHits = self._cumulativeBackwardAngles(dx, dy)
                if revHits.size > 0 or visitedTotal:
                    break

                swept = float(cumTheta[-1])
                if swept > 1e-3:
                    estWin = int(math.ceil(winSize * (2.0 * np.pi / swept) * 1.75))
                    nextWin = max(winSize * 4, min(totalLen, max(1024, estWin)))
                else:
                    nextWin = max(winSize * 8, 1024)
                winSize = min(totalLen, nextWin)
            else:
                if visitedTotal:
                    break
                winSize = min(totalLen, max(1024, winSize * 8))

        if dx is None or dx.size == 0:
            return None, None

        if revHits is not None and revHits.size > 0:
            revIdx = int(revHits[0])
            segStart = (dx.size - 2) - revIdx
            orbitPointsCount = dx.size - segStart
            guardStart = max(0, segStart - 1)
            revDX, revDY = dx[guardStart:], dy[guardStart:]

            if not self._isTrailVisible(revDX, revDY, originX, originY, viewBounds, pixelSizeAU):
                return None, None

            if pixelSizeAU > 0.0:
                screenDiamPx = max(float(revDX.max() - revDX.min()), float(revDY.max() - revDY.min())) / pixelSizeAU
                targetPts = int(np.clip(math.ceil(screenDiamPx * 2.5), 36, 120))
            else:
                targetPts = 120

            if orbitPointsCount < targetPts and revDX.size >= 4:
                dx, dy = self._smoothOrbitPoints(revDX, revDY, targetPoints=targetPts)
                cumTheta, revHits = self._cumulativeBackwardAngles(dx, dy)
                if revHits.size > 0:
                    dx, dy = self._trimToSingleRevolution(dx, dy, cumTheta, int(revHits[0]))
            else:
                dx, dy = self._trimToSingleRevolution(dx, dy, cumTheta, revIdx)
        else:
            if not self._isTrailVisible(dx, dy, originX, originY, viewBounds, pixelSizeAU):
                return None, None

            if 4 <= dx.size < 120 and cumTheta is not None and cumTheta.size > 0:
                totalSweep = float(cumTheta[-1])
                if (totalSweep / dx.size) > (2.0 * np.pi / 90.0):
                    targetPts = max(int(math.ceil(totalSweep / (2.0 * np.pi / 120.0))), dx.size + 4)
                    dx, dy = self._smoothOrbitPoints(dx, dy, targetPoints=min(120, targetPts))

        return originX + dx, originY + dy

    def plotBodyPoints(self, ax, body, bodyIndex, viewBounds=None, pixelSizeAU=None, refSliceCache=None):
        """Plot a body's orbital trail and current marker onto ax."""
        if viewBounds is None:
            viewBounds = (
                -self.simulationSize + self.focusPoint[0],
                self.simulationSize + self.focusPoint[0],
                -self.simulationSize + self.focusPoint[1],
                self.simulationSize + self.focusPoint[1],
            )
        if pixelSizeAU is None:
            pixelSizeAU = (2.0 * self.simulationSize) / 550.0 if self.simulationSize > 0 else 0.0

        trailX, trailY = self.bodyPoints[bodyIndex][0], self.bodyPoints[bodyIndex][1]
        currentX = body[POS][0] / AU_METERS
        currentY = body[POS][1] / AU_METERS

        refIdx = self.getBodyReference(bodyIndex)
        if refIdx != -1 and len(self.bodyPoints[refIdx][0]) > 0:
            refX, refY = self.bodyPoints[refIdx][0], self.bodyPoints[refIdx][1]
            refCurrentX = self.listOfBodies[refIdx][POS][0] / AU_METERS
            refCurrentY = self.listOfBodies[refIdx][POS][1] / AU_METERS
        else:
            refX = refY = None
            refCurrentX = refCurrentY = 0.0

        plotX, plotY = self._extractOrbitTrail(
            trailX,
            trailY,
            currentX,
            currentY,
            refX,
            refY,
            refCurrentX,
            refCurrentY,
            viewBounds=viewBounds,
            pixelSizeAU=pixelSizeAU,
            refIdx=refIdx,
            refSliceCache=refSliceCache,
        )

        colours = body[COLOUR]
        lineColour, markerColour = colours if isinstance(colours, (list, tuple)) else (colours, colours)

        if plotX is not None and plotX.size > 0 and self._isTrailVisible(
            plotX, plotY, 0.0, 0.0, viewBounds, pixelSizeAU, marginRatio=0.0
        ):
            ax.plot(plotX, plotY, color=lineColour)

        minViewX, maxViewX, minViewY, maxViewY = viewBounds
        markerMargin = 0.05 * self.simulationSize if self.simulationSize > 0 else 0.0
        if (
            minViewX - markerMargin <= currentX <= maxViewX + markerMargin
            and minViewY - markerMargin <= currentY <= maxViewY + markerMargin
        ):
            ax.plot(currentX, currentY, "o", color=markerColour)
        return ax

    def updateFocusPoint(self):
        """Synchronize focusPoint and focusBodyName with the currently selected focusBody."""
        if self.focusBody < 0 or self.focusBody >= len(self.listOfBodies):
            self.focusBody = -1
            self.focusPoint = [0, 0]
            self.focusBodyName = "None"
        else:
            chosenFocusBody = self.listOfBodies[self.focusBody]
            self.focusPoint = [chosenFocusBody[POS][0] / AU_METERS, chosenFocusBody[POS][1] / AU_METERS]
            self.focusBodyName = chosenFocusBody[NAME]

    @staticmethod
    def _appendPointsForBody(points, xAU, yAU, zAU, vx, vy, vz):
        """Append one 3D sample to a body's history and cap growth at MAX_HISTORY_POINTS."""
        if len(points) < 4:
            points.append([0.0] * len(points[0]))
        points[0].append(float(xAU))
        points[1].append(float(yAU))
        points[2][0].append(float(vx))
        points[2][1].append(float(vy))
        points[2][2].append(float(vz))
        points[3].append(float(zAU))

        if len(points[0]) > MAX_HISTORY_POINTS + 500:
            points[0] = points[0][-MAX_HISTORY_POINTS:]
            points[1] = points[1][-MAX_HISTORY_POINTS:]
            points[2][0] = points[2][0][-MAX_HISTORY_POINTS:]
            points[2][1] = points[2][1][-MAX_HISTORY_POINTS:]
            points[2][2] = points[2][2][-MAX_HISTORY_POINTS:]
            points[3] = points[3][-MAX_HISTORY_POINTS:]

    def updateStoredPath(self):
        """Append each body's current position (in AU) and velocity (in m/s) to bodyPoints."""
        for bodyNumber, body in enumerate(self.listOfBodies):
            pos = body[POS]
            vel = body[VEL]
            self._appendPointsForBody(
                self.bodyPoints[bodyNumber],
                pos[0] / AU_METERS,
                pos[1] / AU_METERS,
                pos[2] / AU_METERS,
                vel[0],
                vel[1],
                vel[2],
            )

    def _appendStoredPathFromArrays(self, pos, vel):
        """Append NumPy position and velocity arrays directly to bodyPoints."""
        invAU = 1.0 / AU_METERS
        for bodyNumber in range(len(self.listOfBodies)):
            self._appendPointsForBody(
                self.bodyPoints[bodyNumber],
                pos[bodyNumber, 0] * invAU,
                pos[bodyNumber, 1] * invAU,
                pos[bodyNumber, 2] * invAU,
                vel[bodyNumber, 0],
                vel[bodyNumber, 1],
                vel[bodyNumber, 2],
            )

    def tickSimulation(self):
        """Advance the simulation by one tick on the scalar path after resolving any collisions."""
        self._resolveCollisions()
        bodies = self.listOfBodies
        n = len(bodies)
        isFilterTick = self.ticksPerStorageUpdate > 0 and (
            self.simulationTime % self.ticksPerStorageUpdate == 0
        )

        if isFilterTick:
            activePairs = []
            for i in range(n):
                body1 = bodies[i]
                for j in range(i + 1, n):
                    if self._applyPairGravity(body1, bodies[j], filterTick=True):
                        activePairs.append((i, j))
            self._activePairs = activePairs
        else:
            if self._activePairs is None:
                self._activePairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
            for i, j in self._activePairs:
                self._applyPairGravity(bodies[i], bodies[j], filterTick=False)

        dt = self.secondsPerSimulationTick
        for body in bodies:
            pos = body[POS]
            vel = body[VEL]
            pos[0] += vel[0] * dt
            pos[1] += vel[1] * dt
            pos[2] += vel[2] * dt

        if isFilterTick:
            self.updateStoredPath()

    def _packNumpyState(self):
        """Pack current listOfBodies state into contiguous float64 NumPy arrays."""
        bodies = self.listOfBodies
        pos = np.array([b[POS] for b in bodies], dtype=np.float64)
        vel = np.array([b[VEL] for b in bodies], dtype=np.float64)
        mass = np.array([b[MASS] for b in bodies], dtype=np.float64)
        rad = np.array([b[RADIUS] for b in bodies], dtype=np.float64)
        radSumSq = (rad[:, None] + rad[None, :]) ** 2
        np.fill_diagonal(radSumSq, -1.0)
        return pos, vel, mass, radSumSq

    def _syncNumpyState(self, pos, vel):
        """Write vectorized NumPy positions and velocities back into listOfBodies."""
        for i, body in enumerate(self.listOfBodies):
            body[POS][0] = float(pos[i, 0])
            body[POS][1] = float(pos[i, 1])
            body[POS][2] = float(pos[i, 2])
            body[VEL][0] = float(vel[i, 0])
            body[VEL][1] = float(vel[i, 1])
            body[VEL][2] = float(vel[i, 2])

    def _runSimulationNumpy(self, targetTicks):
        """Advance N >= NUMPY_BODY_THRESHOLD systems using exact vectorized all-pairs gravity."""
        if self._resolveCollisions() and len(self.listOfBodies) < NUMPY_BODY_THRESHOLD:
            return
        pos, vel, mass, radSumSq = self._packNumpyState()
        dt = float(self.secondsPerSimulationTick)

        while targetTicks is None or self.simulationTime < targetTicks:
            diff = pos[None, :, :] - pos[:, None, :]
            distSq = np.einsum("ijk,ijk->ij", diff, diff)
            np.fill_diagonal(distSq, np.inf)

            if np.any(distSq <= radSumSq):
                self._syncNumpyState(pos, vel)
                self._resolveCollisions()
                if len(self.listOfBodies) < NUMPY_BODY_THRESHOLD:
                    return
                pos, vel, mass, radSumSq = self._packNumpyState()
                continue

            invD3 = G / (distSq * np.sqrt(distSq))
            np.fill_diagonal(invD3, 0.0)
            acc = np.einsum("ij,j,ijk->ik", invD3, mass, diff)
            vel += acc * dt
            pos += vel * dt

            if self.ticksPerStorageUpdate > 0 and self.simulationTime % self.ticksPerStorageUpdate == 0:
                self._appendStoredPathFromArrays(pos, vel)

            self.simulationTime += 1

        self._syncNumpyState(pos, vel)
        self.invalidatePairCache()

    def runSimulation(self, setTicks=None):
        """Advance the simulation until targetTicks (or indefinitely if setTicks is None)."""
        targetTicks = None
        if setTicks is not None:
            targetTicks = round(setTicks)
            if targetTicks <= self.simulationTime:
                return

        startTime = self.simulationTime
        if len(self.listOfBodies) >= NUMPY_BODY_THRESHOLD:
            self._runSimulationNumpy(targetTicks)

        while targetTicks is None or self.simulationTime < targetTicks:
            self.tickSimulation()
            self.simulationTime += 1

        if (
            targetTicks is not None
            and self.simulationTime > startTime
            and self.ticksPerPageUpdate < self.ticksPerStorageUpdate
        ):
            self.updateStoredPath()

    def loadTemplates(self, templateNumber=0):
        """Populate engine bodies and timing parameters from SYSTEM_TEMPLATES."""
        template = SYSTEM_TEMPLATES.get(templateNumber, SYSTEM_TEMPLATES[4])
        dt = template["dt"]
        self.listOfBodies = [_makeBody(*b) for b in template["bodies"]]
        self.secondsPerSimulationTick = dt
        self.simulationSize = template["size"]
        self.ticksPerStorageUpdate = round(template["storageSeconds"] / dt)
        self.ticksPerPageUpdate = round(template["pageSeconds"] / dt)
        self.simulationName = template["name"]
        self.bodyPoints = [[[], [], [[], [], []], []] for _ in self.listOfBodies]
        self.invalidatePairCache()

    def rollbackSimulation(self):
        """Roll back the simulation by one page-update interval without rendering."""
        storedValuesPerUpdate = (
            max(1, round(self.ticksPerPageUpdate / self.ticksPerStorageUpdate))
            if self.ticksPerStorageUpdate > 0 else 0
        )
        poppedAny = False
        for _ in range(storedValuesPerUpdate):
            for index, body in enumerate(self.listOfBodies):
                points = self.bodyPoints[index]
                if not points[0]:
                    continue
                body[POS][0] = points[0].pop() * AU_METERS
                body[POS][1] = points[1].pop() * AU_METERS
                body[VEL][0] = points[2][0].pop()
                body[VEL][1] = points[2][1].pop()
                body[VEL][2] = points[2][2].pop()
                if len(points) > 3 and points[3]:
                    body[POS][2] = points[3].pop() * AU_METERS
                poppedAny = True

        if poppedAny:
            self.simulationTime = max(0, self.simulationTime - self.ticksPerPageUpdate)
        self.invalidatePairCache()
