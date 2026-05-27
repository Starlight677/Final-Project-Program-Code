import math as Math

import matplotlib.pyplot as plt

class TwoBodyTesting:
    def __init__(self):
        pass

    def tickSimulation(self, body1Coords, body2Coords, body1Motion, body2Motion, body1Mass,
                       body2Mass, body1Radius, body2Radius, secondsPerSimulationTick = 1):
        # Add existing motion to new motion from gravity
        try:
            body1Acceleration = self.checkGravityMotionChange(body1Coords, body2Coords,
                                                              body2Mass, body1Radius, body2Radius)
            body2Acceleration = self.checkGravityMotionChange(body2Coords, body1Coords,
                                                              body1Mass, body2Radius, body1Radius)

            body1Motion = self.modifyListContents(body1Motion, body1Acceleration, "+", secondsPerSimulationTick)
            body2Motion = self.modifyListContents(body2Motion, body2Acceleration, "+", secondsPerSimulationTick)

            return body1Motion, body2Motion
        except:
            return False

    def modifyListContents(self, list1, list2, modifier, valueMultiplier = 1):
        # Adds or multiplies together the contents of two lists
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
        # Calculates the distances (axis and total) between the two bodies
        bodyDistances = [body1Coords[0] - body2Coords[0], body1Coords[1] - body2Coords[1],
                         body1Coords[2] - body2Coords[2]]
        bodyTotalDistance = Math.sqrt(bodyDistances[0] ** 2 + bodyDistances[1] ** 2 + bodyDistances[2] ** 2)
        return bodyDistances, bodyTotalDistance

    def checkGravityMotionChange(self, targetBodyCoords, pullingBodyCoords, pullingBodyMass,
                                 targetBodyRadius, pullingBodyRadius):
        bodyDistances, bodyTotalDistance = self.determineDistances(targetBodyCoords, pullingBodyCoords)

        if bodyTotalDistance <= targetBodyRadius + pullingBodyRadius:
            return False
        # Calculate gravity
        G = 6.6743*10**-11 #Gravitational constant
        pullingBodyGravity = (G*pullingBodyMass)/bodyTotalDistance**2

        # Give velocity change
        distanceModifier = abs(pullingBodyGravity/bodyTotalDistance)
        targetBodyMotion = [-(x*distanceModifier) for x in bodyDistances]
        return targetBodyMotion

    def runSimulation(self):
        # Useful constants for defining planet parameters
        solarMass = 1.989e30
        earthMass = 5.972e24

        # Set starting values for bodies
        # Order: coordinates, motion, mass, radius and colours (trail then dot colour)
        body1Stats = [[0,0,0], [0, 0, 0], solarMass * 1, 7e7, ['yellow', 'yellow']] # The Sun
        body2Stats = [[-1.521e11,0,0], [0,29290,0], earthMass * 1, 6.3e5, ['blue', 'blue']] # The Earth (at aphelion)
        body3Stats = [[1.082e11, 0, 0], [0, -35000, 0], earthMass * 0.815, 6.05e5, ['orange', 'orange']] # Venus
        body4Stats = [[0,2.064e11,0], [26490,0,0], earthMass * 0.107, 3.396e5, ['red', 'red']] # Mars (at perihelion)
        body5Stats = [[0,-6.982e10,0], [-38900,0,0], earthMass * 0.055, 2.439e5, ['brown', 'brown']] # Mercury (at aphelion)
        listOfBodies = [body1Stats, body2Stats, body3Stats, body4Stats, body5Stats]

        simulationTime = 0
        simulationSize = 3e11 # Size of the screen in meters
        secondsPerSimuationTick = 60 # Seconds per simulation tick
        ticksPerDisplayUpdate = (86400*5)/secondsPerSimuationTick # One graph update per 5 days
        ticksPerStorageUpdata = 3600/secondsPerSimuationTick # One course point saved every hour
        bodyCollision = False

        #Create list for previous positions of planets
        bodyPoints = [[[],[]]]
        for i in range(len(listOfBodies) - 1):
            bodyPoints.append([[],[]])

        while not bodyCollision:
            # Run the simulation for a tick + update timer
            try:
                bodyNumber = 0
                while bodyNumber < len(listOfBodies):
                    # Iterate through every combination of bodies once
                    secondBodyNumber = bodyNumber + 1
                    while secondBodyNumber < len(listOfBodies):
                        body1Stats = listOfBodies[bodyNumber]
                        body2Stats = listOfBodies[secondBodyNumber]

                        body1Stats[1], body2Stats[1]= (
                            self.tickSimulation(body1Stats[0], body2Stats[0], body1Stats[1], body2Stats[1],
                                                body1Stats[2], body2Stats[2], body1Stats[3], body2Stats[3],
                                                secondsPerSimuationTick))
                        listOfBodies[bodyNumber] = body1Stats
                        listOfBodies[secondBodyNumber] = body2Stats
                        secondBodyNumber = secondBodyNumber + 1

                    # Update position of each body after all influences are calculated
                    body1Stats = listOfBodies[bodyNumber]
                    body1Stats[0] = self.modifyListContents(body1Stats[0], body1Stats[1], "+", secondsPerSimuationTick)
                    listOfBodies[bodyNumber] = body1Stats
                    bodyNumber = bodyNumber + 1

            except:
                bodyCollision = True
                print("Simulation Terminated upon Body Collision")
            simulationTime = simulationTime + 1

            if simulationTime % ticksPerDisplayUpdate == 0: # Number of ticks simulated per frame shown to user
                #For each body, add current point to list of positions
                bodyCount = 0
                for body in listOfBodies:
                    bodyPoints[bodyCount][0].append(body[0][0])
                    bodyPoints[bodyCount][1].append(body[0][1])
                    bodyCount = bodyCount + 1

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

            elif simulationTime % ticksPerStorageUpdata == 0:
                # Add current point to list of positions
                bodyCount = 0
                for body in listOfBodies:
                    bodyPoints[bodyCount][0].append(body[0][0])
                    bodyPoints[bodyCount][1].append(body[0][1])
                    bodyCount = bodyCount + 1