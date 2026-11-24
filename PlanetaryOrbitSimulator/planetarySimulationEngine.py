import math

import matplotlib
matplotlib.use('agg')  # Headless backend for Django worker threads
import matplotlib.pyplot as plt
import numpy as np

plt.style.use("fast")
matplotlib.rcParams['path.simplify'] = True
matplotlib.rcParams['path.simplify_threshold'] = 0.2

G = 6.6743e-11
AU_METERS = 1.495979e11
SOLAR_MASS = 1.989e30
EARTH_MASS = 5.972e24
MOON_MASS = EARTH_MASS * 0.0123
SECONDS_PER_DAY = 86400
SIGNIFICANCE_THRESHOLD = 1e-6

# Indices into each body entry: [pos, vel, mass, radius, [line_colour, marker_colour], name, ref_index]
POS, VEL, MASS, RADIUS, COLOUR, NAME, REF = range(7)


class _BodyCollision(Exception):
    """Internal signal raised when two bodies overlap during a gravity step."""

    def __init__(self, body1Index, body2Index):
        self.body1Index = body1Index
        self.body2Index = body2Index


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
    99: {
        # Disabled from UI selection due to complexity / long runtimes
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
            ((-596411065182.7, 0.0, 0.0), (0.0, -3471.3, 0.0), EARTH_MASS * 0.00018, 3.98e5, "gold", "Pyroifoi RD-Z d1-223 6 a", 15),
            ((0.0, 950720000000.0, 0.0), (-13675.0, 0.0, 0.0), SOLAR_MASS * 0.011719, 7e7 * 0.0603, "darkmagenta", "Pyroifoi RD-Z d1-223 7", 0),
            ((1937555573.4, 950720000000.0, 0.0), (-13675.0, 28336.0, 0.0), EARTH_MASS * 0.006953, 1.33e6, "silver", "Pyroifoi RD-Z d1-223 7 a", 17),
            ((0.0, 953432368185.1, 0.0), (-37624.2, 0.0, 0.0), EARTH_MASS * 0.006178, 1.28e6, "silver", "Pyroifoi RD-Z d1-223 7 b", 17),
            ((-3458488009.2, 950720000000.0, 0.0), (-13675.0, -21209.1, 0.0), EARTH_MASS * 0.005175, 1.21e6, "sandybrown", "Pyroifoi RD-Z d1-223 7 c", 17),
            ((-0.0, 945995000660.1, 0.0), (4470.3, -0.0, 0.0), EARTH_MASS * 0.004555, 1.16e6, "silver", "Pyroifoi RD-Z d1-223 7 d", 17),
            ((4509413714.8, 955229413714.8, 0.0), (-24719.2, 11044.2, 0.0), EARTH_MASS * 0.003913, 1.10e6, "silver", "Pyroifoi RD-Z d1-223 7 e", 17),
            ((-6672850099.7, 957392850099.7, 0.0), (-22754.0, -9079.0, 0.0), EARTH_MASS * 0.02264, 1.96e6, "silver", "Pyroifoi RD-Z d1-223 7 f", 17),
            ((0.0, 997120000000.0, 0.0), (-7836.0, 0.0, 0.0), EARTH_MASS * 69.959572, 4.04e7, "peru", "Pyroifoi RD-Z d1-223 8", 0),
            ((1403700000000.0, 0.0, 0.0), (0.0, 11209.0, 0.0), EARTH_MASS * 2188.751709, 7.08e7, "mediumblue", "Pyroifoi RD-Z d1-223 9", 0),
            ((1404319433363.4, 0.0, 0.0), (0.0, 48737.7, 0.0), EARTH_MASS * 0.16297, 3.48e6, "lightsteelblue", "Pyroifoi RD-Z d1-223 9 a", 25),
            ((1403700000000.0, 1106238462.6, 0.0), (-28082.6, 11209.0, 0.0), EARTH_MASS * 0.202102, 3.73e6, "sandybrown", "Pyroifoi RD-Z d1-223 9 b", 25),
            ((1401586677626.1, 0.0, 0.0), (-0.0, -9108.9, 0.0), EARTH_MASS * 0.787346, 5.67e6, "orangered", "Pyroifoi RD-Z d1-223 9 c", 25),
            ((1403700000000.0, -4934228254.2, 0.0), (13296.9, 11209.0, 0.0), EARTH_MASS * 12.583962, 3.20e7, "peru", "Pyroifoi RD-Z d1-223 9 d", 25),
            ((1409717486834.0, 6017486834.0, 0.0), (-7159.5, 18368.5, 0.0), EARTH_MASS * 42.22065, 4.55e7, "whitesmoke", "Pyroifoi RD-Z d1-223 9 e", 25),
            ((1409977787956.3, 6017486834.0, 0.0), (-7159.5, 26409.0, 0.0), EARTH_MASS * 0.03382, 2.82e6, "snow", "Pyroifoi RD-Z d1-223 9 e a", 30),
            ((1460000000000.0, 0.0, 0.0), (0.0, 7253.0, 0.0), EARTH_MASS * 20.416899, 1.76e7, "snow", "Pyroifoi RD-Z d1-223 10", 0),
        ),
    },
}

TEMPLATE_NAMES = [SYSTEM_TEMPLATES[i]["name"] for i in range(5)]


class PlanetarySimulationEngine:
    """N-body gravitational simulator with adaptive pair filtering and orbital trail rendering."""

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
        if isinstance(refIndex, bool) or not isinstance(refIndex, int) or refIndex < 0 or refIndex >= len(self.listOfBodies) or refIndex == bodyIndex:
            refIndex = -1
        body = self.listOfBodies[bodyIndex]
        if len(body) > REF:
            body[REF] = refIndex
        else:
            body.append(refIndex)

    def _applyPairGravity(self, body1, body2, filterTick):
        """
        Apply mutual gravitational impulse to body1 and body2 using Newton's third law.
        Returns whether the pair exceeds the significance threshold, or None on collision.
        """
        pos1, pos2 = body1[POS], body2[POS]
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        dz = pos1[2] - pos2[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        if dist <= body1[RADIUS] + body2[RADIUS]:
            return None

        invDistCubed = G / (dist * dist * dist)
        mod1 = abs(body2[MASS] * invDistCubed)
        mod2 = abs(body1[MASS] * invDistCubed)

        a1x, a1y, a1z = -dx * mod1, -dy * mod1, -dz * mod1
        a2x, a2y, a2z = dx * mod2, dy * mod2, dz * mod2

        exceedsThreshold = (
            (abs(a1x) + abs(a1y) + abs(a1z)) >= SIGNIFICANCE_THRESHOLD
            or (abs(a2x) + abs(a2y) + abs(a2z)) >= SIGNIFICANCE_THRESHOLD
        )

        # Batch below-threshold pairs over the full storage interval in one pass
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

    def cycleBody(self, bodyNumber, filterMask, fullCompanions, filterTick=False):
        """Calculate gravitational interactions for bodyNumber and advance its position."""
        significantCompanions = (
            [fullCompanions[j][bodyNumber] for j in range(bodyNumber)] + [False]
            if filterTick else None
        )

        body1 = self.listOfBodies[bodyNumber]
        for secondBodyNumber in range(bodyNumber + 1, len(self.listOfBodies)):
            if filterTick or filterMask[secondBodyNumber]:
                isOverThreshold = self._applyPairGravity(
                    body1, self.listOfBodies[secondBodyNumber], filterTick
                )
                if isOverThreshold is None:
                    raise _BodyCollision(bodyNumber, secondBodyNumber)
                if filterTick:
                    significantCompanions.append(isOverThreshold)

        pos = body1[POS]
        vel = body1[VEL]
        dt = self.secondsPerSimulationTick
        pos[0] += vel[0] * dt
        pos[1] += vel[1] * dt
        pos[2] += vel[2] * dt

        return significantCompanions

    def mergeCollidingBodies(self, body1Index, body2Index, significantCompanions):
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
        mergedRef = dominant[REF] if len(dominant) > REF and isinstance(dominant[REF], int) else -1
        if mergedRef in (body1Index, body2Index):
            mergedRef = -1

        self.listOfBodies[body1Index] = _makeBody(
            mergedCoords, mergedMotion, totalMass, mergedRadius, mergedColour, mergedName, mergedRef
        )
        self.listOfBodies.pop(body2Index)
        self.bodyPoints.pop(body2Index)

        updatedCompanions = [
            [entry for j, entry in enumerate(row) if j != body2Index]
            for i, row in enumerate(significantCompanions)
            if i != body2Index
        ]
        # Force full gravity checks on the merged body until the next filter tick
        for i, row in enumerate(updatedCompanions):
            if i == body1Index:
                updatedCompanions[i] = [j != body1Index for j in range(len(row))]
            elif body1Index < len(row):
                row[body1Index] = True

        if self.focusBody == body2Index:
            self.focusBody = -1
            self.focusBodyName = "None"
        else:
            if self.focusBody > body2Index:
                self.focusBody -= 1
            if self.focusBody == body1Index:
                self.focusBodyName = mergedName

        for body in self.listOfBodies:
            if len(body) > REF and isinstance(body[REF], int):
                if body[REF] == body2Index:
                    body[REF] = -1
                elif body[REF] > body2Index:
                    body[REF] -= 1

        return updatedCompanions

    def drawGraph(self, user, backgroundColour="black", graphColour="white"):
        """Render the current orbital state and trails to the user's PNG file."""
        self.updateFocusPoint()

        fig, ax = plt.subplots(figsize=(6.9, 6.9))
        fig.set_facecolor(backgroundColour)
        ax.set_facecolor(backgroundColour)
        ax.set_aspect('equal', adjustable='box')

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

        for bodyIndex in range(len(self.listOfBodies) - 1, -1, -1):
            try:
                self.plotBodyPoints(ax, self.listOfBodies[bodyIndex], bodyIndex, viewBounds, pixelSizeAU)
            except IndexError:
                continue

        fig.savefig(f"media/latestSimulation{user.username}.png")
        plt.close(fig)

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
            if (originX + xMax + marginX < minViewX or
                    originX + xMin - marginX > maxViewX or
                    originY + yMax + marginY < minViewY or
                    originY + yMin - marginY > maxViewY):
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
    def _sliceTrailWindow(trailX, trailY, startIdx, totalLen, stride, refXPoints=None, refYPoints=None):
        """Slice (trailX, trailY) and subtract reference body slices when provided."""
        tx = np.asarray(trailX[startIdx:totalLen:stride], dtype=float)
        ty = np.asarray(trailY[startIdx:totalLen:stride], dtype=float)
        if refXPoints is None or refYPoints is None:
            return tx, ty
        rx = np.asarray(refXPoints[startIdx:totalLen:stride], dtype=float)
        ry = np.asarray(refYPoints[startIdx:totalLen:stride], dtype=float)
        return tx - rx, ty - ry

    def _extractOrbitTrail(self, trailX, trailY, currentX, currentY,
                           refXPoints=None, refYPoints=None, refCurrentX=0.0, refCurrentY=0.0,
                           viewBounds=None, pixelSizeAU=0.0):
        """
        Extract a single-revolution orbital trail in world coordinates in O(1) time
        using angular-rate guided tail windows and early viewport/sub-pixel culling.
        """
        useRelative = refXPoints is not None and refYPoints is not None
        totalLen = min(len(trailX), len(refXPoints)) if useRelative else len(trailX)
        if totalLen == 0:
            return None, None

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
                trailX, trailY, startIdx, totalLen, stride,
                refXPoints if useRelative else None, refYPoints if useRelative else None,
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

    def plotBodyPoints(self, ax, body, bodyIndex, viewBounds=None, pixelSizeAU=None):
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
            trailX, trailY, currentX, currentY,
            refX, refY, refCurrentX, refCurrentY,
            viewBounds=viewBounds, pixelSizeAU=pixelSizeAU,
        )

        colours = body[COLOUR]
        lineColour, markerColour = colours if isinstance(colours, (list, tuple)) else (colours, colours)

        if plotX is not None and plotX.size > 0 and self._isTrailVisible(
            plotX, plotY, 0.0, 0.0, viewBounds, pixelSizeAU, marginRatio=0.0
        ):
            ax.plot(plotX, plotY, color=lineColour)

        minViewX, maxViewX, minViewY, maxViewY = viewBounds
        markerMargin = 0.05 * self.simulationSize if self.simulationSize > 0 else 0.0
        if (minViewX - markerMargin <= currentX <= maxViewX + markerMargin and
                minViewY - markerMargin <= currentY <= maxViewY + markerMargin):
            ax.plot(currentX, currentY, 'o', color=markerColour)
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

    def updateStoredPath(self):
        """Append each body's current position (in AU) and velocity (in m/s) to bodyPoints."""
        for bodyNumber, body in enumerate(self.listOfBodies):
            points = self.bodyPoints[bodyNumber]
            points[0].append(body[POS][0] / AU_METERS)
            points[1].append(body[POS][1] / AU_METERS)
            points[2][0].append(body[VEL][0])
            points[2][1].append(body[VEL][1])
            points[2][2].append(body[VEL][2])

    def tickSimulation(self, significantCompanions):
        """Advance the simulation by one tick, resolving any body collisions."""
        isFilterTick = self.ticksPerStorageUpdate > 0 and (
            self.simulationTime % self.ticksPerStorageUpdate == 0
        )
        bodyNumber = 0
        while bodyNumber < len(self.listOfBodies):
            try:
                result = self.cycleBody(
                    bodyNumber, significantCompanions[bodyNumber], significantCompanions, isFilterTick
                )
                if isFilterTick:
                    significantCompanions[bodyNumber] = result
                bodyNumber += 1
            except _BodyCollision as col:
                significantCompanions = self.mergeCollidingBodies(
                    col.body1Index, col.body2Index, significantCompanions
                )
                print(f"Body Collision resolved between body {col.body1Index} and body {col.body2Index}.")
                bodyNumber = 0

        if isFilterTick:
            self.updateStoredPath()

        return significantCompanions

    def runSimulation(self, user, backgroundStyle, axisStyle, setTicks=-1):
        """Run the simulation until targetTicks (or indefinitely if setTicks < 0) and render."""
        numBodies = len(self.listOfBodies)
        significantCompanions = [[True] * numBodies for _ in range(numBodies)]
        targetTicks = round(setTicks) if setTicks >= 0 else -1

        timePassed = False
        while targetTicks < 0 or self.simulationTime < targetTicks:
            significantCompanions = self.tickSimulation(significantCompanions)
            self.simulationTime += 1
            timePassed = True

        if targetTicks >= 0:
            if timePassed and self.ticksPerPageUpdate < self.ticksPerStorageUpdate:
                self.updateStoredPath()
            self.drawGraph(user, backgroundStyle, axisStyle)

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
        self.bodyPoints = [[[], [], [[], [], []]] for _ in self.listOfBodies]

    def rollbackSimulation(self, user, backgroundStyle, axisStyle):
        """Roll back the simulation by one page-update interval and redraw."""
        storedValuesPerUpdate = (
            round(self.ticksPerPageUpdate / self.ticksPerStorageUpdate)
            if self.ticksPerStorageUpdate else 0
        )
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

        self.simulationTime = max(0, self.simulationTime - self.ticksPerPageUpdate)
        self.drawGraph(user, backgroundStyle, axisStyle)
