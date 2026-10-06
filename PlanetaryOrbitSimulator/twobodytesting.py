import math as Math

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

class PlanetarySimulationEngine:

    def __init__(self):
        self.listOfBodies = []
        self.simulationTime = 0
        self.simulationSize = 0
        self.focusPoint = [0,0] # Coordinates of focus window
        self.focusBody = -1
        self.focusBodyName = "None"
        self.bodyPoints = []
        self.ticksPerStorageUpdate = 0
        self.ticksPerPageUpdate = 0
        self.secondsPerSimulationTick = 0
        self.simulationName = ""
        self.collidedPlanets = []
        pass

    def getBodyReference(self, bodyIndex):
        """Returns the reference body index for bodyIndex (-1 for static grid)."""
        if bodyIndex < 0 or bodyIndex >= len(self.listOfBodies):
            return -1
        body = self.listOfBodies[bodyIndex]
        ref = body[6]
        if ref >= len(self.listOfBodies) or ref == bodyIndex:
            # Return no reference body if error
            return -1
        return ref

    def getBodyReferenceName(self, bodyIndex):
        """Returns the display name of the reference body for bodyIndex."""
        ref = self.getBodyReference(bodyIndex)
        if ref == -1:
            return "None (Static Grid)"
        return self.listOfBodies[ref][5]

    def setBodyReference(self, bodyIndex, refIndex):
        """Sets the reference body index for bodyIndex."""
        if bodyIndex < 0 or bodyIndex >= len(self.listOfBodies):
            return
        body = self.listOfBodies[bodyIndex]
        if refIndex < -1 or refIndex >= len(self.listOfBodies) or refIndex == bodyIndex:
            refIndex = -1
        body[6] = refIndex
        self.listOfBodies[bodyIndex] = body

    def tickBodyPair(self, body1Coords, body2Coords, body1Motion, body2Motion, body1Mass,
                       body2Mass, body1Radius, body2Radius, secondsMultiplier):
        # Get acceleration of bodies from each other's gravity
        body1Acceleration = self.checkGravityMotionChange(body1Coords, body2Coords,
                                                          body2Mass, body1Radius, body2Radius)
        body2Acceleration = self.checkGravityMotionChange(body2Coords, body1Coords,
                                                          body1Mass, body2Radius, body1Radius)

        # Return error if bodies have collided (calculated in gravity check method)
        if body1Acceleration == False or body2Acceleration == False:
            print(body1Coords, body2Coords)
            return False

        # Used for checking if a body's influence is significant or not
        if sum(np.abs(body1Acceleration)) >= 0.01 or sum(np.abs(body2Acceleration)) >= 0.01:
            exceedsThreshold = True
        else:
            exceedsThreshold = False

        # Add existing motion to new motion from gravity
        body1Motion = self.addAcceleration(body1Motion, body1Acceleration, secondsMultiplier)
        body2Motion = self.addAcceleration(body2Motion, body2Acceleration, secondsMultiplier)

        return body1Motion, body2Motion, exceedsThreshold

    def addAcceleration(self, bodyMotion, bodyAcceleration, valueMultiplier = 1):
        # Adds together the contents of two lists, with a multiplier
        # used for accounting for seconds per tick
        for i in range(len(bodyMotion)):
            bodyMotion[i] = bodyMotion[i] + bodyAcceleration[i] * valueMultiplier
        return bodyMotion

    def determineDistances(self, body1Coords, body2Coords):
        # Calculates the distances (per-axis and total) between the two bodies
        bodyDistances = [body1Coords[0] - body2Coords[0], body1Coords[1] - body2Coords[1],
                         body1Coords[2] - body2Coords[2]]
        bodyTotalDistance = Math.sqrt((bodyDistances[0] ** 2) + (bodyDistances[1] ** 2) +
                                      (bodyDistances[2] ** 2))
        return bodyDistances, bodyTotalDistance

    def checkGravityMotionChange(self, targetBodyCoords, pullingBodyCoords, pullingBodyMass,
                                 targetBodyRadius, pullingBodyRadius):
        # Get the distance between the bodies
        bodyDistances, bodyTotalDistance = self.determineDistances(targetBodyCoords, pullingBodyCoords)

        # If the two bodies have collided, return error
        if bodyTotalDistance <= targetBodyRadius + pullingBodyRadius:
            print(targetBodyCoords, pullingBodyCoords)
            return False

        # Calculate gravity of pulling body at this distance
        G = 6.6743*10**-11 #Gravitational constant
        pullingBodyGravity = (G*pullingBodyMass)/bodyTotalDistance**2

        # Give velocity change of target body
        distanceModifier = abs(pullingBodyGravity/bodyTotalDistance)
        targetBodyMotion = [-(x*distanceModifier) for x in bodyDistances]
        return targetBodyMotion

    def cycleBody(self, bodyNumber, filterMask, fullCompanions, filterTick = False):
        #Calculate gravitational interaction for possible pairs of bodies
        significantCompanions = []
        if filterTick == True:
            #Iterate through the already processed pairs - mirror the filter mask check
            secondBodyNumber = 0
            while secondBodyNumber < bodyNumber:
                significantCompanions.append(fullCompanions[secondBodyNumber][bodyNumber])
                secondBodyNumber = secondBodyNumber + 1
            significantCompanions.append(False) # Add one filler entry for a planet's relation to itself
            secondBodyNumber = secondBodyNumber + 1
        else:
            # Since lower-numbered bodies have already been calculated, don't need to do it again
            secondBodyNumber = bodyNumber + 1

        while secondBodyNumber < len(self.listOfBodies):
            if filterTick == True or filterMask[secondBodyNumber] == True:
                # Pull stats of both bodies out of the list
                body1Stats = self.listOfBodies[bodyNumber]
                body2Stats = self.listOfBodies[secondBodyNumber]

                if filterTick == True and filterMask[secondBodyNumber] == False:
                    # Process body pair for overall time if below significance threshold
                    body1Stats[1], body2Stats[1], isOverThreshold = (
                            self.tickBodyPair(body1Stats[0], body2Stats[0], body1Stats[1], body2Stats[1],
                                    body1Stats[2], body2Stats[2], body1Stats[3], body2Stats[3],
                                    self.secondsPerSimulationTick * self.ticksPerStorageUpdate))
                else:
                    body1Stats[1], body2Stats[1], isOverThreshold = (
                        self.tickBodyPair(body1Stats[0], body2Stats[0], body1Stats[1], body2Stats[1],
                                          body1Stats[2], body2Stats[2], body1Stats[3], body2Stats[3],
                                          self.secondsPerSimulationTick))

                if filterTick and isOverThreshold:
                    significantCompanions.append(True)
                elif filterTick:
                    significantCompanions.append(False)

                self.listOfBodies[bodyNumber] = body1Stats
                self.listOfBodies[secondBodyNumber] = body2Stats
            # Go to next second body
            secondBodyNumber = secondBodyNumber + 1

        # Update position of the processed body after all influences are calculated
        body1Stats = self.listOfBodies[bodyNumber]
        body1Stats[0] = self.addAcceleration(body1Stats[0], body1Stats[1], self.secondsPerSimulationTick)
        self.listOfBodies[bodyNumber] = body1Stats

        if filterTick:
            # Return significant companions list if calculating it
            return significantCompanions
        else:
            pass

    def PlanetaryCollisionHandling(self, body1Index, body2Index, significantCompanions):
        """
        Merges two colliding bodies into one, conserving momentum and volume.

        The surviving body (body1Index) absorbs body2Index:
          - Position   : centre of mass of the two bodies
          - Velocity   : conserved momentum  (m1*v1 + m2*v2) / (m1 + m2)
          - Mass       : m1 + m2
          - Radius     : volume-conserving   (r1^3 + r2^3)^(1/3)
          - Colour     : kept from the more-massive body
          - Name       : kept from the more-massive body

        The absorbed body (body2Index) is then removed from listOfBodies,
        bodyPoints, and significantCompanions.

        Returns the updated significantCompanions list (now one entry shorter).
        """
        body1Stats = self.listOfBodies[body1Index]
        body2Stats = self.listOfBodies[body2Index]

        m1 = body1Stats[2]
        m2 = body2Stats[2]
        totalMass = m1 + m2

        # Centre-of-mass position
        mergedCoords = [
            (m1 * body1Stats[0][i] + m2 * body2Stats[0][i]) / totalMass
            for i in range(3)
        ]

        # Conservation of momentum → merged velocity
        mergedMotion = [
            (m1 * body1Stats[1][i] + m2 * body2Stats[1][i]) / totalMass
            for i in range(3)
        ]

        # Volume-conserving radius  r = (r1³ + r2³)^(1/3)
        mergedRadius = (body1Stats[3] ** 3 + body2Stats[3] ** 3) ** (1 / 3)

        # Keep the appearance/name of the more-massive body
        if m1 >= m2:
            mergedColour = body1Stats[4]
            mergedName   = body1Stats[5]
        else:
            mergedColour = body2Stats[4]
            mergedName   = body2Stats[5]

        # Build the merged body and write it back into the survivor slot
        mergedBody = [mergedCoords, mergedMotion, totalMass, mergedRadius,
                      mergedColour, mergedName]
        self.listOfBodies[body1Index] = mergedBody

        # Remove the absorbed body from every tracking structure
        self.listOfBodies.pop(body2Index)
        self.bodyPoints.pop(body2Index)

        # Rebuild significantCompanions to match the new body count
        updatedCompanions = []
        for i, row in enumerate(significantCompanions):
            if i == body2Index:
                continue  # Drop the absorbed body's row entirely
            newRow = [entry for j, entry in enumerate(row) if j != body2Index]
            updatedCompanions.append(newRow)

        # If the focus body was the absorbed one, clear focus; if it was above
        # the removed index, shift the index down by one to stay on target.
        if self.focusBody == body2Index:
            self.focusBody = -1
            self.focusBodyName = "None"
        elif self.focusBody > body2Index:
            self.focusBody -= 1

        # Clean up per-body references across surviving bodies
        for b in self.listOfBodies:
            if len(b) > 6 and isinstance(b[6], int):
                if b[6] == body2Index:
                    b[6] = -1
                elif b[6] > body2Index:
                    b[6] -= 1

        return updatedCompanions

    def drawGraph(self, user, backgroundColour = "black", graphColour = "white"):
        # Draw a graph using MatPlotLib
        matplotlib.use('agg') # Mode for not having issues with Django threading
        plt.style.use("fast")
        self.updateFocusPoint() # Plot the boundaries of the graph

        fig = plt.figure(figsize=(6.9, 6.9))
        ax = fig.add_subplot()
        fig.set_facecolor(backgroundColour)
        ax.set_facecolor(backgroundColour)
        ax.set_aspect('equal', adjustable='box')

        # Change the color of the x-axis
        ax.spines['bottom'].set_color(graphColour)
        ax.tick_params(axis="x", colors=graphColour)
        ax.xaxis.label.set_color(graphColour)

        # Change the color of the y-axis
        ax.spines['left'].set_color(graphColour)
        ax.tick_params(axis="y", colors=graphColour)
        ax.yaxis.label.set_color(graphColour)

        # Fill in the top and right of the graph
        ax.spines['top'].set_color(graphColour)
        ax.spines['right'].set_color(graphColour)

        plt.xlim((-self.simulationSize)+self.focusPoint[0], self.simulationSize+self.focusPoint[0])
        plt.ylim((-self.simulationSize)+self.focusPoint[1], self.simulationSize+self.focusPoint[1])
        plt.xlabel("Distance (AU)")
        plt.ylabel("Distance (AU)")
        plt.grid(True)

        AU = 1.495979e11
        # For each body, draw both the line of previous path and marker of current position.
        # Each body can have its orbit path drawn relative to another body's position.
        for i, body in enumerate(reversed(self.listOfBodies)):
            try:
                bodyIndex = len(self.listOfBodies) - (i + 1)
                self.plotBodyPoints(plt, body, bodyIndex)
            except IndexError:  # If point not found for body, continue
                continue

        # Save graph to file
        plt.savefig('media/latestSimulation' + user.username + '.png')
        plt.close('all')

    def plotBodyPoints(self, plt, body, bodyIndex):
        # Plot the points for a specific body on the graph
        trailX = self.bodyPoints[bodyIndex][0]  # Already in AU
        trailY = self.bodyPoints[bodyIndex][1]
        AU = 1.495979e11
        currentX = body[0][0] / AU
        currentY = body[0][1] / AU

        refBodyIndex = self.getBodyReference(bodyIndex) # Get index fo body to draw around
        useRelativeFrame = (
                refBodyIndex != -1
                and refBodyIndex < len(self.listOfBodies)
                and refBodyIndex != bodyIndex
                and len(self.bodyPoints[refBodyIndex][0]) > 0
        )

        if useRelativeFrame: # Draw orbit lines around reference body
            refXPoints = self.bodyPoints[refBodyIndex][0]
            refYPoints = self.bodyPoints[refBodyIndex][1]
            refCurrentX = self.listOfBodies[refBodyIndex][0][0] / AU
            refCurrentY = self.listOfBodies[refBodyIndex][0][1] / AU

            minLen = min(len(trailX), len(refXPoints))
            if minLen > 0:
                offsetTrailX = [refCurrentX + (trailX[k] - refXPoints[k]) for k in range(minLen)]
                offsetTrailY = [refCurrentY + (trailY[k] - refYPoints[k]) for k in range(minLen)]
                plt.plot(offsetTrailX, offsetTrailY, color=body[4][0])
            plt.plot(currentX, currentY, 'o', color=body[4][1])
        else:
            # Draw flat orbit lines
            plt.plot(trailX, trailY, color=body[4][0])
            plt.plot(currentX, currentY, 'o', color=body[4][1])
        return plt

    def updateFocusPoint(self):
        if self.focusBody == -1 or self.focusBody >= len(self.listOfBodies):
            self.focusBody = -1
            self.focusPoint = [0,0]
            self.focusBodyName = "None"
        else:
            AU = 1.495979e11
            chosenFocusBody = self.listOfBodies[self.focusBody]
            self.focusPoint = [chosenFocusBody[0][0]/AU, chosenFocusBody[0][1]/AU]
            self.focusBodyName = chosenFocusBody[5]

    def detectCollidingPair(self):
        """
        Scans all body pairs and returns the indices (i, j) of the first pair
        whose separation is less than or equal to the sum of their radii.
        Returns (None, None) if no collision is currently detected.
        """
        for i in range(len(self.listOfBodies)):
            for j in range(i + 1, len(self.listOfBodies)):
                bodyA = self.listOfBodies[i]
                bodyB = self.listOfBodies[j]
                _, dist = self.determineDistances(bodyA[0], bodyB[0])
                if dist <= bodyA[3] + bodyB[3]:
                    return i, j
        return None, None

    def updateStoredPath(self):
        AU = 1.495979e11
        for bodyNumber, body in enumerate(
            self.listOfBodies):  # Add current points of planets (in AU) to list for display
            self.bodyPoints[bodyNumber][0].append(body[0][0] / AU)
            self.bodyPoints[bodyNumber][1].append(body[0][1] / AU)
            self.bodyPoints[bodyNumber][2][0].append(body[1][0])  # Add velocity for reload storage purposes
            self.bodyPoints[bodyNumber][2][1].append(body[1][1])
            self.bodyPoints[bodyNumber][2][2].append(body[1][2])

    def tickSimulation(self, significantCompanions):
        bodyCollision = False
        if self.simulationTime % self.ticksPerStorageUpdate == 0:
            # Add current point to list of positions
            bodyNumber = 0
            while bodyNumber < len(self.listOfBodies):
                try:
                    # Iterate through every combination of bodies once
                    bodySignificantCompanions = self.cycleBody(bodyNumber, significantCompanions[bodyNumber], significantCompanions, True)
                    significantCompanions[bodyNumber] = bodySignificantCompanions
                    bodyNumber = bodyNumber + 1
                except:
                    # A collision was detected inside cycleBody — find and merge the pair
                    i, j = self.detectCollidingPair()
                    if i is not None:
                        self.collidedPlanets.append((i, j))
                        significantCompanions = self.PlanetaryCollisionHandling(i, j, significantCompanions)
                        print(f"Body Collision resolved between body {i} and body {j}.")
                        # Restart the loop from the beginning with the updated body list
                        bodyNumber = 0
                    else:
                        # Collision pair not found; halt as a fallback
                        bodyCollision = True
                        print("Body Collision — could not identify pair, halting.")
                        break

            self.updateStoredPath() # Save the current locations of the planets for path plotting

        else:
            # Run the simulation for a tick
            bodyNumber = 0
            while bodyNumber < len(self.listOfBodies):
                try:
                    # Iterate through every combination of bodies once
                    self.cycleBody(bodyNumber, significantCompanions[bodyNumber], significantCompanions)
                    bodyNumber = bodyNumber + 1
                except:
                    # A collision was detected inside cycleBody — find and merge the pair
                    i, j = self.detectCollidingPair()
                    if i is not None:
                        self.collidedPlanets.append((i, j))
                        significantCompanions = self.PlanetaryCollisionHandling(i, j, significantCompanions)
                        print(f"Body Collision resolved between body {i} and body {j}.")
                        # Restart the loop from the beginning with the updated body list
                        bodyNumber = 0
                    else:
                        # Collision pair not found; halt as a fallback
                        bodyCollision = True
                        print("Body Collision — could not identify pair, halting.")
                        break

        return significantCompanions, bodyCollision

    def runSimulation(self, user, backgroundStyle, axisStyle, setTicks = -1):
        # Useful constants for defining planet parameters
        bodyCollision = False # Records whether any objects have collided

        #Construct lists for previous positions of planets and pair significance checks
        significantCompanions = []
        for i in range(len(self.listOfBodies)): # One entry to save a planet's coordinates
            companionsEntry = []
            for j in range(len(self.listOfBodies)): # One list per planet of every other planet
                companionsEntry.append([])
            significantCompanions.append(companionsEntry)

        timePassed = False
        while not bodyCollision and not setTicks == self.simulationTime:
            significantCompanions, bodyCollision = self.tickSimulation(significantCompanions)
            # Update timer
            self.simulationTime = self.simulationTime + 1
            timePassed = True

        if setTicks == self.simulationTime:
            if timePassed:
                self.updateStoredPath() # Add current position to simulation time period if simulation has moved
            self.drawGraph(user, backgroundStyle, axisStyle)
            pass
        elif bodyCollision:
            # If two planets have collided, exit simulation loop
            pass

    def loadTemplates(self, templateNumber = 0):
        solarMass = 1.989e30
        earthMass = 5.972e24
        moonMass = earthMass * 0.0123
        if templateNumber == 0: # Inner Solar System planets
            body1Stats = [[0, 0, 0], [0, 0, 0], solarMass * 1, 7e8, ['yellow', 'yellow'], "The Sun", -1]
            body2Stats = [[0, -6.982e10, 0], [-38900, 0, 0], earthMass * 0.055, 2.439e6,
                          ['darkgrey', 'darkgrey'], "Mercury", 0]  # Mercury (at aphelion)
            body3Stats = [[1.082e11, 0, 0], [0, -35000, 0], earthMass * 0.815, 6.05e6,
                          ['orange', 'orange'], "Venus", 0]  # Venus
            body4Stats = [[-1.521e11, 0, 0], [0, 29290, 0], earthMass * 1, 6.3e6,
                          ['blue', 'blue'], "The Earth", 0]  # The Earth (at aphelion)
            body5Stats = [[-1.521e11, 3.84e8, 0], [1022, 29290, 0], moonMass * 1, 1.738e6,
                          ['silver', 'silver'], "The Moon", 3]  # The Moon (relative to Earth)
            body6Stats = [[0, 2.064e11, 0], [26490, 0, 0], earthMass * 0.107, 3.396e6,
                          ['red', 'red'], "Mars", 0]  # Mars (at perihelion)
            self.listOfBodies = [body1Stats, body2Stats, body3Stats, body4Stats, body5Stats, body6Stats]

            self.secondsPerSimulationTick = 60
            self.simulationSize = 2  # Size of the displayed area in AU
            self.ticksPerStorageUpdate = (3600*12) / self.secondsPerSimulationTick  # One course point saved every 12 hours
            self.ticksPerPageUpdate = round((86400*5)/self.secondsPerSimulationTick) # One update per 5 days
            self.simulationName = "Inner Solar System"

        elif templateNumber == 1:
            # Moons of Jupiter
            body1Stats = [[0, 0, 0], [0, 0, 0], earthMass * 318, 6.989e7,
                          ['darkorange', 'darkorange'], "Jupiter", -1]  # Jupiter
            body2Stats = [[4.217e8, 0, 0], [0, -17334, 0], moonMass * 1.05, 3.643e6,
                          ['gold', 'gold'], "Io", 0]  # Io (relative to Jupiter)
            body3Stats = [[-6.71e8, 0, 0], [0, 13703, 0], moonMass * 0.9, 3.122e6,
                          ['lightsteelblue', 'lightsteelblue'], "Europa", 0]  # Europa (relative to Jupiter)
            body4Stats = [[0, 1.07e9, 0], [10880, 0, 0], moonMass * 2, 5.262e6,
                          ['silver', 'silver'], "Ganymede", 0]  # Ganymede (relative to Jupiter)
            body5Stats = [[0, -1.883e9, 0], [-8204, 0, 0], moonMass * 1.5, 4.821e6,
                          ['grey', 'grey'], "Callisto", 0]  # Callisto (relative to Jupiter)
            self.listOfBodies = [body1Stats, body2Stats, body3Stats, body4Stats, body5Stats]

            self.secondsPerSimulationTick = 6 # 10 simulation ticks per minute
            self.simulationSize = 0.02  # Size of the displayed area in AU
            self.ticksPerStorageUpdate = 3600 / self.secondsPerSimulationTick  # One course point saved every hour
            self.ticksPerPageUpdate = round((86400/4) / self.secondsPerSimulationTick)  # One update per 6 hours
            self.simulationName = "Galilean Moons of Jupiter"

        elif templateNumber == 2:
            # Ascendia system (A star)
            body1Stats = [[0, 0, 0], [0, 0, 0], solarMass * 0.2656, 7e7*0.474,
                          ['orange', 'orange'], "Col 285 Sector ZX-R b5-0 A", -1] # Primary star
            body2Stats = [[-3.3e9, 0, 0], [0, 103364, 0], earthMass * 0.0908, 2.887e6,
                          ['grey', 'grey'], "Col 285 Sector ZX-R b5-0 A 1", 0]  # A 1
            body3Stats = [[6e9, 0, 0], [0, -76657, 0], earthMass * 0.1077, 3.049e6,
                          ['darkgrey', 'darkgrey'], "Stephenson's Rock", 0]  # Stephenson's Rock
            body4Stats = [[0,-1.04e10, 0], [-58225, 0, 0], earthMass * 0.0965, 2.944e6,
                          ['orangered', 'orangered'], "Col 285 Sector ZX-R b5-0 A 3", 0]  # A 3
            body5Stats = [[0, 1.9e10, 0], [43077, 0, 0], earthMass * 0.1623, 4.434e6,
                          ['lightskyblue', 'lightskyblue'], "Ascendia", 0]  # Ascendia
            body6Stats = [[0, -3.5e10, 0], [-31739, 0, 0], earthMass * 0.3876, 5.802e6,
                          ['silver', 'silver'], "Col 285 Sector ZX-R b5-0 A 5", 0]  # A 5
            body7Stats = [[-6.44e10, 0, 0], [0, 23398, 0], earthMass * 0.2808, 5.27e6,
                          ['silver', 'silver'], "Col 285 Sector ZX-R b5-0 A 6", 0]  # A 6
            self.listOfBodies = [body1Stats, body2Stats, body3Stats, body4Stats, body5Stats, body6Stats, body7Stats]
            self.secondsPerSimulationTick = 60
            self.simulationSize = 0.5  # Size of the displayed area in AU
            self.ticksPerStorageUpdate = (3600*3) / self.secondsPerSimulationTick  # One course point saved every 3 hours
            self.ticksPerPageUpdate = round((86400/2) / self.secondsPerSimulationTick)  # One update per 12 hours
            self.simulationName = "Ascendia Primary Star"
        elif templateNumber == 3:
            # Binary Stars
            body1Stats = [[-7.51e10, 0, 0], [0, 11000, 0], solarMass * 1, 7e7,
                          ['yellow', 'yellow'], "Primary Star", -1] # Primary star
            body2Stats = [[1.521e11, 0, 0], [0, -22000, 0], solarMass * 0.5, 5e7,
                          ['orange', 'orange'], "Secondary Star", -1] # Secondary star
            self.listOfBodies = [body1Stats, body2Stats]
            self.secondsPerSimulationTick = 60
            self.simulationSize = 2  # Size of the displayed area in AU
            self.ticksPerStorageUpdate = (3600*12) / self.secondsPerSimulationTick  # One course point saved every 12 hours
            self.ticksPerPageUpdate = round((86400 * 30) / self.secondsPerSimulationTick)  # One update per 30 days
            self.simulationName = "Binary Stars"
        elif templateNumber == 4:
            # Madman's Halo system (Complete system with all planets and moons)
            body1Stats = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], solarMass * 1.320313, 7e7 * 1.2902, ['white', 'white'], "Pyroifoi RD-Z d1-223", -1]  # F (White) Star
            body2Stats = [[-3300000000.0, 0.0, 0.0], [0.0, 230543.0, 0.0], earthMass * 15.172054, 1.27e+07, ['saddlebrown', 'saddlebrown'], "Pyroifoi RD-Z d1-223 1", 0]  # High metal content world
            body3Stats = [[5700000000.0, 0.0, 0.0], [0.0, -175417.0, 0.0], earthMass * 5.797106, 1.00e+07, ['maroon', 'maroon'], "Pyroifoi RD-Z d1-223 2", 0]  # High metal content world
            # Binary Pair 1: Planets 3 & 4
            body4Stats = [[0.0, -399010000000.0, 0.0], [20968.0, 0.0, 0.0], earthMass * 1342.156738, 7.60e+07, ['mediumblue', 'mediumblue'], "Pyroifoi RD-Z d1-223 3", 0]  # Class III gas giant
            body5Stats = [[643399138.1, -399010000000.0, 0.0], [20968.0, 28835.3, 0.0], earthMass * 0.011476, 1.57e+06, ['gold', 'gold'], "Pyroifoi RD-Z d1-223 3 a", 3]  # Rocky body
            body6Stats = [[1044040809.0, -399010000000.0, 0.0], [20968.0, 23063.4, 0.0], earthMass * 0.010893, 1.55e+06, ['silver', 'silver'], "Pyroifoi RD-Z d1-223 3 b", 3]  # Rocky body
            body7Stats = [[1051164498.5, -399010000000.0, 0.0], [20968.0, 22018.8, 0.0], earthMass * 0.008608, 1.43e+06, ['sandybrown', 'sandybrown'], "Pyroifoi RD-Z d1-223 3 c", 3]  # Rocky body
            body8Stats = [[0.0, -408850000000.0, 0.0], [13591.0, 0.0, 0.0], earthMass * 1.773461, 7.20e+06, ['deepskyblue', 'deepskyblue'], "Madman's Halo", 0]  # Earth-like world
            body9Stats = [[0.0, -408700401992.1, 0.0], [11417.2, 0.0, 0.0], earthMass * 0.000172, 3.93e+05, ['silver', 'silver'], "Pyroifoi RD-Z d1-223 4 a", 7]  # Rocky body
            # Binary Pair 2: Planets 5 & 6
            body10Stats = [[-583690000000.0, 0.0, 0.0], [0.0, -17475.0, 0.0], earthMass * 1308.151978, 7.59e+07, ['mediumblue', 'mediumblue'], "Pyroifoi RD-Z d1-223 5", 0]  # Class III gas giant
            body11Stats = [[-582865087111.6, 0.0, 0.0], [0.0, 7666.3, 0.0], earthMass * 0.004294, 1.14e+06, ['silver', 'silver'], "Pyroifoi RD-Z d1-223 5 a", 9]  # Rocky body
            body12Stats = [[-582862561374.6, 0.0, 0.0], [0.0, 8489.5, 0.0], earthMass * 0.000213, 4.28e+05, ['grey', 'grey'], "Pyroifoi RD-Z d1-223 5 a a", 9]  # Rocky body
            body13Stats = [[-583690000000.0, 1070105762.3, 0.0], [-22073.9, -17475.0, 0.0], earthMass * 0.001776, 8.51e+05, ['silver', 'silver'], "Pyroifoi RD-Z d1-223 5 b", 9]  # Rocky body
            body14Stats = [[-585759554317.0, 0.0, 0.0], [-0.0, -33347.8, 0.0], earthMass * 0.006879, 1.33e+06, ['sandybrown', 'sandybrown'], "Pyroifoi RD-Z d1-223 5 c", 9]  # Rocky body
            body15Stats = [[-583690000000.0, -2694282701.8, 0.0], [13911.4, -17475.0, 0.0], earthMass * 0.006498, 1.31e+06, ['silver', 'silver'], "Pyroifoi RD-Z d1-223 5 d", 9]  # Rocky body
            body16Stats = [[-596630000000.0, 0.0, 0.0], [0.0, -11052.0, 0.0], earthMass * 31.564976, 3.41e+07, ['whitesmoke', 'whitesmoke'], "Pyroifoi RD-Z d1-223 6", 0]  # Class II gas giant
            body17Stats = [[-596411065182.7, 0.0, 0.0], [0.0, -3471.3, 0.0], earthMass * 0.00018, 3.98e+05, ['gold', 'gold'], "Pyroifoi RD-Z d1-223 6 a", 15]  # Rocky body
            # Binary Pair 3: Bodies 7 & 8
            body18Stats = [[0.0, 950720000000.0, 0.0], [-13675.0, 0.0, 0.0], solarMass * 0.011719, 7e7 * 0.0603, ['darkmagenta', 'darkmagenta'], "Pyroifoi RD-Z d1-223 7", 0]  # Y (Brown dwarf) Star
            body19Stats = [[1937555573.4, 950720000000.0, 0.0], [-13675.0, 28336.0, 0.0], earthMass * 0.006953, 1.33e+06, ['silver', 'silver'], "Pyroifoi RD-Z d1-223 7 a", 17]  # Rocky body
            body20Stats = [[0.0, 953432368185.1, 0.0], [-37624.2, 0.0, 0.0], earthMass * 0.006178, 1.28e+06, ['silver', 'silver'], "Pyroifoi RD-Z d1-223 7 b", 17]  # Rocky body
            body21Stats = [[-3458488009.2, 950720000000.0, 0.0], [-13675.0, -21209.1, 0.0], earthMass * 0.005175, 1.21e+06, ['sandybrown', 'sandybrown'], "Pyroifoi RD-Z d1-223 7 c", 17]  # Rocky body
            body22Stats = [[-0.0, 945995000660.1, 0.0], [4470.3, -0.0, 0.0], earthMass * 0.004555, 1.16e+06, ['silver', 'silver'], "Pyroifoi RD-Z d1-223 7 d", 17]  # Rocky body
            body23Stats = [[4509413714.8, 955229413714.8, 0.0], [-24719.2, 11044.2, 0.0], earthMass * 0.003913, 1.10e+06, ['silver', 'silver'], "Pyroifoi RD-Z d1-223 7 e", 17]  # Rocky body
            body24Stats = [[-6672850099.7, 957392850099.7, 0.0], [-22754.0, -9079.0, 0.0], earthMass * 0.02264, 1.96e+06, ['silver', 'silver'], "Pyroifoi RD-Z d1-223 7 f", 17]  # Rocky body
            body25Stats = [[0.0, 997120000000.0, 0.0], [-7836.0, 0.0, 0.0], earthMass * 69.959572, 4.04e+07, ['peru', 'peru'], "Pyroifoi RD-Z d1-223 8", 0]  # Gas giant with ammonia-based life
            # Binary Pair 4: Planets 9 & 10
            body26Stats = [[1403700000000.0, 0.0, 0.0], [0.0, 11209.0, 0.0], earthMass * 2188.751709, 7.08e+07, ['mediumblue', 'mediumblue'], "Pyroifoi RD-Z d1-223 9", 0]  # Class III gas giant
            body27Stats = [[1404319433363.4, 0.0, 0.0], [0.0, 48737.7, 0.0], earthMass * 0.16297, 3.48e+06, ['lightsteelblue', "lightsteelblue"], "Pyroifoi RD-Z d1-223 9 a", 25]  # High metal content world
            body28Stats = [[1403700000000.0, 1106238462.6, 0.0], [-28082.6, 11209.0, 0.0], earthMass * 0.202102, 3.73e+06, ['sandybrown', 'sandybrown'], "Pyroifoi RD-Z d1-223 9 b", 25]  # High metal content world
            body29Stats = [[1401586677626.1, 0.0, 0.0], [-0.0, -9108.9, 0.0], earthMass * 0.787346, 5.67e+06, ['orangered', 'orangered'], "Pyroifoi RD-Z d1-223 9 c", 25]  # High metal content world
            body30Stats = [[1403700000000.0, -4934228254.2, 0.0], [13296.9, 11209.0, 0.0], earthMass * 12.583962, 3.20e+07, ['peru', 'peru'], "Pyroifoi RD-Z d1-223 9 d", 25]  # Gas giant with ammonia-based life
            body31Stats = [[1409717486834.0, 6017486834.0, 0.0], [-7159.5, 18368.5, 0.0], earthMass * 42.22065, 4.55e+07, ['whitesmoke', 'whitesmoke'], "Pyroifoi RD-Z d1-223 9 e", 25]  # Class I gas giant
            body32Stats = [[1409977787956.3, 6017486834.0, 0.0], [-7159.5, 26409.0, 0.0], earthMass * 0.03382, 2.82e+06, ['snow', 'snow'], "Pyroifoi RD-Z d1-223 9 e a", 30]  # Icy body
            body33Stats = [[1460000000000.0, 0.0, 0.0], [0.0, 7253.0, 0.0], earthMass * 20.416899, 1.76e+07, ['snow', 'snow'], "Pyroifoi RD-Z d1-223 10", 0]  # Icy body
            self.listOfBodies = [body1Stats, body2Stats, body3Stats, body4Stats, body5Stats, body6Stats,
                                 body7Stats, body8Stats, body9Stats, body10Stats, body11Stats, body12Stats,
                                 body13Stats, body14Stats, body15Stats, body16Stats, body17Stats, body18Stats,
                                 body19Stats, body20Stats, body21Stats, body22Stats, body23Stats, body24Stats,
                                 body25Stats, body26Stats, body27Stats, body28Stats, body29Stats, body30Stats,
                                 body31Stats, body32Stats, body33Stats]
            self.secondsPerSimulationTick = 600 # One simulation tick per 10 minutes
            self.simulationSize = 11  # Size of the displayed area in AU
            self.ticksPerStorageUpdate = 3600 / self.secondsPerSimulationTick  # One course point saved every hour
            self.ticksPerPageUpdate = round((86400 * 30) / self.secondsPerSimulationTick)  # One update per 30 days
            self.simulationName = "Madman's Halo"
        else:
            # Display only a star if error in choosing starter configuration
            body1Stats = [[0, 0, 0], [0, 0, 0], solarMass * 1, 7e7, ['yellow', 'yellow'], "Primary Star", -1]
            self.listOfBodies = [body1Stats]
            self.secondsPerSimulationTick = 60
            self.simulationSize = 1  # Size of the displayed area in meters
            self.ticksPerStorageUpdate = (3600*12) / self.secondsPerSimulationTick  # One course point saved every 12 hours
            self.ticksPerPageUpdate = round((86400 * 5) / self.secondsPerSimulationTick)  # One update per 5 days
            self.simulationName = "Single Star"

        # Construct the BodyPoints list with a structured entry per body
        self.bodyPoints = []
        for i in range(len(self.listOfBodies)):
            self.bodyPoints.append([[], [], [[],[],[]]])

    def rollbackSimulation(self, user, backgroundStyle, axisStyle):
        # Roll back the simulation
        storedValuesPerUpdate = round(self.ticksPerPageUpdate/self.ticksPerStorageUpdate)
        AU = 1.495979e11
        # For each body, iterate through the stored points backwards
        for i in range(storedValuesPerUpdate):
            try:
                for index, body in enumerate(self.listOfBodies):
                    body[0][0] = self.bodyPoints[index][0].pop()*AU
                    body[0][1] = self.bodyPoints[index][1].pop()*AU
                    body[1][0] = self.bodyPoints[index][2][0].pop()
                    body[1][1] = self.bodyPoints[index][2][1].pop()
                    body[1][2] = self.bodyPoints[index][2][2].pop()
                    self.listOfBodies[index] = body
            except IndexError: # If an added body doesn't have any points left
                pass

        self.simulationTime = self.simulationTime - self.ticksPerPageUpdate
        self.drawGraph(user, backgroundStyle, axisStyle)
        pass
