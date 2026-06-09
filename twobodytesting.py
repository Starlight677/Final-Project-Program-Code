import math as Math

import matplotlib.pyplot as plt
import numpy as np

class TwoBodyTesting:
    def __init__(self):
        pass

    def tickBodyPair(self, body1Coords, body2Coords, body1Motion, body2Motion, body1Mass,
                       body2Mass, body1Radius, body2Radius, secondsPerSimulationTick = 1):
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
        if sum(np.abs(body1Acceleration)) >= 0.001 or sum(np.abs(body2Acceleration)) >= 0.001:
            exceedsThreshold = True
        else:
            exceedsThreshold = False

        # Add existing motion to new motion from gravity
        body1Motion = self.modifyListContents(body1Motion, body1Acceleration, "+", secondsPerSimulationTick)
        body2Motion = self.modifyListContents(body2Motion, body2Acceleration, "+", secondsPerSimulationTick)

        return body1Motion, body2Motion, exceedsThreshold

    def modifyListContents(self, list1, list2, modifier, valueMultiplier = 1):
        # Adds or multiplies together the contents of two lists, with a multiplier
        # used for accounting for seconds per tick
        if len(list1) == len(list2):
            if modifier == "+":
                for i in range(len(list1)):
                    list1[i] = list1[i] + list2[i] * valueMultiplier
            elif modifier == "*":
                for i in range(len(list1)):
                    list1[i] = list1[i] * list2[i] * valueMultiplier
            return list1
        else:
            return list1

    def determineDistances(self, body1Coords, body2Coords):
        # Calculates the distances (per-axis and total) between the two bodies
        bodyDistances = [body1Coords[0] - body2Coords[0], body1Coords[1] - body2Coords[1],
                         body1Coords[2] - body2Coords[2]]
        bodyTotalDistance = Math.sqrt(bodyDistances[0] ** 2 + bodyDistances[1] ** 2 + bodyDistances[2] ** 2)
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

    def cycleBody(self, listOfBodies, bodyNumber, secondsPerSimuationTick, filterMask, fullCompanions, filterTick = False):
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

        while secondBodyNumber < len(listOfBodies):
            if filterTick == True or filterMask[secondBodyNumber] == True:
                # Pull stats of both bodies out of the list
                body1Stats = listOfBodies[bodyNumber]
                body2Stats = listOfBodies[secondBodyNumber]

                if filterTick == True and filterMask[secondBodyNumber] == False:
                    # Process body pair for overall time if below significance threshold
                    body1Stats[1], body2Stats[1], isOverThreshold = (
                            self.tickBodyPair(body1Stats[0], body2Stats[0], body1Stats[1], body2Stats[1],
                                    body1Stats[2], body2Stats[2], body1Stats[3], body2Stats[3],
                                    secondsPerSimuationTick*60))
                else:
                    body1Stats[1], body2Stats[1], isOverThreshold = (
                        self.tickBodyPair(body1Stats[0], body2Stats[0], body1Stats[1], body2Stats[1],
                                          body1Stats[2], body2Stats[2], body1Stats[3], body2Stats[3],
                                          secondsPerSimuationTick))

                if filterTick and isOverThreshold:
                    significantCompanions.append(True)
                elif filterTick:
                    significantCompanions.append(False)

                listOfBodies[bodyNumber] = body1Stats
                listOfBodies[secondBodyNumber] = body2Stats
            # Go to next second body
            secondBodyNumber = secondBodyNumber + 1

        # Update position of the processed body after all influences are calculated
        body1Stats = listOfBodies[bodyNumber]
        body1Stats[0] = self.modifyListContents(body1Stats[0], body1Stats[1], "+", secondsPerSimuationTick)
        listOfBodies[bodyNumber] = body1Stats

        if filterTick:
            # Return significant companions list if calculating it
            return listOfBodies, significantCompanions
        else:
            return listOfBodies

    def runSimulation(self):
        # Useful constants for defining planet parameters
        solarMass = 1.989e30
        earthMass = 5.972e24

        # Set starting values for bodies
        # Order: coordinates, motion, mass, radius and display colours (trail then dot colour)
        body1Stats = [[0,0,0], [0, 0, 0], solarMass * 1, 7e7, ['yellow', 'yellow']] # The Sun
        body2Stats = [[-1.521e11,0,0], [0,29290,0], earthMass * 1, 6.3e5, ['blue', 'blue']] # The Earth (at aphelion)
        body3Stats = [[1.082e11, 0, 0], [0, -35000, 0], earthMass * 0.815, 6.05e5, ['orange', 'orange']] # Venus
        body4Stats = [[0,2.064e11,0], [26490,0,0], earthMass * 0.107, 3.396e5, ['red', 'red']] # Mars (at perihelion)
        body5Stats = [[0,-6.982e10,0], [-38900,0,0], earthMass * 0.055, 2.439e5, ['brown', 'brown']] # Mercury (at aphelion)
        body6Stats = [[-1.521e11, 3.84e7,0],[1022,29290,0], earthMass*0.0123, 1.738e5, ['grey', 'grey']] # The Moon
        listOfBodies = [body1Stats, body6Stats, body3Stats, body4Stats, body5Stats, body2Stats]

        simulationTime = 0 # Time in ticks the simulation has run
        simulationSize = 3e11 # Size of the displayed area in meters
        secondsPerSimuationTick = 60 # Seconds per simulation tick
        ticksPerDisplayUpdate = (86400*5)/secondsPerSimuationTick # One graph update per 5 days
        ticksPerStorageUpdate = 3600/secondsPerSimuationTick # One course point saved every hour
        bodyCollision = False # Records whether any objects have collided

        #Construct lists for previous positions of planets and pair significance checks
        bodyPoints = []
        significantCompanions = []
        for i in range(len(listOfBodies)):
            bodyPoints.append([[],[]]) # One entry to save a planet's coordinates
            companionsEntry = []
            for j in range(len(listOfBodies)): # One list per planet of every other planet
                companionsEntry.append([])
            significantCompanions.append(companionsEntry)

        while not bodyCollision:
            if simulationTime % ticksPerStorageUpdate == 0:
                # Add current point to list of positions
                try:
                    bodyNumber = 0
                    while bodyNumber < len(listOfBodies):
                        # Iterate through every combination of bodies once
                        listOfBodies, bodySignificantCompanions = self.cycleBody(listOfBodies, bodyNumber, secondsPerSimuationTick, significantCompanions[bodyNumber], significantCompanions,True)
                        significantCompanions[bodyNumber] = bodySignificantCompanions
                        bodyNumber = bodyNumber + 1
                except:
                    #Stop simulation if planets have collided
                    bodyCollision = True
                    print("Simulation Terminated upon Body Collision")

                bodyNumber = 0
                for body in listOfBodies: # Add current points of planets to list for display
                    bodyPoints[bodyNumber][0].append(body[0][0])
                    bodyPoints[bodyNumber][1].append(body[0][1])
                    bodyNumber = bodyNumber + 1

            else:
                # Run the simulation for a tick
                try:
                    bodyNumber = 0
                    while bodyNumber < len(listOfBodies):
                        # Iterate through every combination of bodies once
                        self.cycleBody(listOfBodies, bodyNumber, secondsPerSimuationTick, significantCompanions[bodyNumber], significantCompanions)
                        bodyNumber = bodyNumber + 1
                except:
                    # Stop simulation if planets have collided
                    bodyCollision = True
                    print("Simulation Terminated upon Body Collision")

            if simulationTime % ticksPerDisplayUpdate == 0: # Number of ticks simulated per frame shown to user
                # Wipe previous content and reconfigure graph
                plt.ion()
                plt.clf()
                plt.xlim(-simulationSize, simulationSize)
                plt.ylim(-simulationSize, simulationSize)
                plt.xlabel("Distance (m)")
                plt.ylabel("Distance (m)")
                dayCount = round((simulationTime/86400)*secondsPerSimuationTick)
                plt.text(simulationSize*-0.4, simulationSize*1.1, "Simulation Time: " + str(dayCount) + " days")

                # For each body, draw both the line of previous path and marker of current position
                bodyCount = 0
                for body in listOfBodies:
                    plt.plot(bodyPoints[bodyCount][0], bodyPoints[bodyCount][1], color=body[4][0])
                    plt.plot(body[0][0], body[0][1], 'o', color=body[4][1])
                    bodyCount = bodyCount + 1

                # Draw graph
                plt.show(block=False)
                plt.pause(0.5)

            #Update timer
            simulationTime = simulationTime + 1
