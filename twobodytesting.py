import math as Math
import time

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

class TwoBodyTesting:
    def __init__(self):
        pass

    def tickSimulation(self, body1Coords, body2Coords, body1Motion, body2Motion, body1Mass,
                       body2Mass):
        # Add existing motion to new motion from gravity
        body1MotionChange = self.checkGravityMotionChange(body1Coords, body2Coords, body2Mass)
        body2MotionChange = self.checkGravityMotionChange(body2Coords, body1Coords, body1Mass)

        body1Motion = self.modifyListContents(body1Motion, body1MotionChange, "+")
        body2Motion = self.modifyListContents(body2Motion, body2MotionChange, "+")

        # Update positions of bodies with their current motion
        body1Coords = self.modifyListContents(body1Coords, body1Motion, "+")
        body2Coords = self.modifyListContents(body2Coords, body2Motion, "+")

        return body1Coords, body2Coords, body1Motion, body2Motion

    def modifyListContents(self, list1, list2, modifier):
        # Adds or multiplies together the contents of two lists
        if len(list1) == len(list2):
            if modifier == "+":
                for i in range(len(list1)):
                    list1[i] = list1[i] + list2[i]
            elif modifier == "*":
                for i in range(len(list1)):
                    list1[i] = list1[i] * list2[i]
            return list1
        else:
            return list1

    def determineDistances(self, body1Coords, body2Coords):
        # Calculates the distances (axis and total) between the two bodies
        bodyDistances = [body1Coords[0] - body2Coords[0], body1Coords[1] - body2Coords[1],
                         body1Coords[2] - body2Coords[2]]
        bodyTotalDistance = Math.sqrt(bodyDistances[0] ** 2 + bodyDistances[1] ** 2 + bodyDistances[2] ** 2)
        return bodyDistances, bodyTotalDistance

    def checkGravityMotionChange(self, targetBodyCoords, pullingBodyCoords, pullingBodyMass):
        bodyDistances, bodyTotalDistance = self.determineDistances(targetBodyCoords, pullingBodyCoords)

        # Calculate gravity
        G = 6.6743*10**-11 #Gravitational constant
        pullingBodyGravity = (G*pullingBodyMass)/bodyTotalDistance**2

        # Give velocity change
        distanceModifier = abs(pullingBodyGravity/bodyTotalDistance)
        targetBodyMotion = [-(x*distanceModifier) for x in bodyDistances]
        return targetBodyMotion

    def runSimulation(self):
        solarMass = 1.989e30
        earthMass = 5.972e24

        # Set starting values
        body1Coords = [0,0,0]
        body2Coords = [-1.496e11,0,0]
        body1Motion = [0,-1.5,0]
        body2Motion = [0,29780,0]
        body1Mass = solarMass * 1 # Mass in Earth/Solar masses
        body2Mass = earthMass * 1

        simulationTime = 0
        simulationSize = 2e11
        simulationTicksPerUpdate = 86400*7 # One graph update per X days

        #Create list for previous positions of planets
        body1PointsX = []
        body1PointsY = []
        body2PointsX = []
        body2PointsY = []

        while True:
            # Run the simulation for a tick + update timer
            body1Coords, body2Coords, body1Motion, body2Motion= (
                self.tickSimulation(body1Coords, body2Coords, body1Motion, body2Motion,
                                    body1Mass, body2Mass))
            simulationTime = simulationTime + 1

            if simulationTime % simulationTicksPerUpdate == 0: # Number of ticks simulated per frame shown to user
                #Add current point to list of positions
                body1PointsX.append(body1Coords[0])
                body1PointsY.append(body1Coords[1])
                body2PointsX.append(body2Coords[0])
                body2PointsY.append(body2Coords[1])

                # Wipe previous content and reconfigure graph
                plt.ion()
                plt.clf()
                plt.xlim(-simulationSize, simulationSize)
                plt.ylim(-simulationSize, simulationSize)
                plt.xlabel("Distance (m)")
                plt.ylabel("Distance (m)")
                plt.text(simulationSize*-0.4, simulationSize*1.1, "Simulation Time: " + str(simulationTime/86400) + " days")

                # Draw both the line of previous path and marker of current position
                plt.plot(body1PointsX, body1PointsY, color='orange')
                plt.plot(body2PointsX, body2PointsY, color='green')
                A = plt.plot(body1Coords[0], body1Coords[1], 'o', color='yellow')
                B = plt.plot(body2Coords[0], body2Coords[1], 'o', color='blue')

                # Draw graph
                plt.show(block=False)
                plt.pause(1)

            elif simulationTime % 5000 == 0:
                # Add current point to list of positions
                body1PointsX.append(body1Coords[0])
                body1PointsY.append(body1Coords[1])
                body2PointsX.append(body2Coords[0])
                body2PointsY.append(body2Coords[1])