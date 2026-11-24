from django.contrib.auth.models import User
from django.db import models


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

    def __str__(self):
        return self.name or f"Simulation {self.pk}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=0)
    backgroundStylePreference = models.TextField(default="black")
    axisStylePreference = models.TextField(default="white")

    def __str__(self):
        return f"{self.user.username} profile"
