from django.db import models
from django.contrib.auth.models import User

class StoredSimulation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=0)
    listOfBodies = models.JSONField(default=list, blank=True)
    simulationSize = models.FloatField(default=0)
    simulationTime = models.IntegerField(default=0)
    bodyPoints = models.JSONField(default=list, blank=True)
    ticksPerStorageUpdate = models.IntegerField(default=0)
    ticksPerPageUpdate = models.IntegerField(default=0)
    secondsPerSimulationTick = models.IntegerField(default=0)
    name = models.TextField(default="")
    image = models.ImageField(default="")