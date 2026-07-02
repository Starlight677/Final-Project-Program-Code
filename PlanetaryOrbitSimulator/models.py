from django.db import models

class StoredSimulation(models.Model):
    listOfBodies = models.JSONField(default=list, blank=True)
    simulationSize = models.IntegerField(default=0)
    simulationTime = models.IntegerField(default=0)
    bodyPoints = models.JSONField(default=list, blank=True)
    ticksPerStorageUpdate = models.IntegerField(default=0)
    ticksPerPageUpdate = models.IntegerField(default=0)
    secondsPerSimulationTick = models.IntegerField(default=0)