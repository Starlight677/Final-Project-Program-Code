import math as Math
import time

class TwoBodyTesting:
    def __init__(self):
        pass

    def tickSimulation(self, body1Coords, body2Coords, body1Motion, body2Motion, body1Mass, body2Mass):
        # Add existing motion to new motion from gravity
        body1MotionChange = self.checkGravityMotionChange(body1Coords, body2Coords, body2Mass)
        body2MotionChange = self.checkGravityMotionChange(body2Coords, body1Coords, body1Mass)

        body1Motion = self.modifyListContents(body1Motion, body1MotionChange, "+")
        body2Motion = self.modifyListContents(body2Motion, body2MotionChange, "+")

        # Update positions of bodies
        body1Coords = self.modifyListContents(body1Coords, body1Motion, "+")
        body2Coords = self.modifyListContents(body2Coords, body2Motion, "+")

        return body1Coords, body2Coords, body1Motion, body2Motion

    def modifyListContents(self, list1, list2, modifier):
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


    def checkGravityMotionChange(self, targetBodyCoords, pullingBodyCoords, pullingBodyMass):
        bodyDistances = [targetBodyCoords[0] - pullingBodyCoords[0], targetBodyCoords[1] - pullingBodyCoords[1], targetBodyCoords[2] - pullingBodyCoords[2]]
        bodyTotalDistance = Math.sqrt(bodyDistances[0]**2 + bodyDistances[1]**2 + bodyDistances[2]**2)

        # Calculate gravity (temporary equation, not real values)
        G = 0.001 #6.6743*10**-11 #Gravitational constant
        pullingBodyGravity = (G*pullingBodyMass)/bodyTotalDistance**2

        # Give velocity change
        distanceModifier = abs(pullingBodyGravity/bodyTotalDistance)
        targetBodyMotion = [-(x*distanceModifier) for x in bodyDistances]
        return targetBodyMotion

    def runSimulation(self):
        body1Coords = [20,20,20]
        body2Coords = [0,0,0]
        body1Motion = [0,-0.0005,0]
        body2Motion = [0,0.001,0]
        body1Mass = 1
        body2Mass = 0.5
        i = 0

        while True:
            body1Coords, body2Coords, body1Motion, body2Motion = (
                self.tickSimulation(body1Coords, body2Coords, body1Motion, body2Motion, body1Mass, body2Mass))
            i = i + 1
            time.sleep(0.0005)
            if i == 500:
                print("Body 1 Coordinates: ", body1Coords)
                print("Body 2 Coordinates: ", body2Coords)
                i = 0