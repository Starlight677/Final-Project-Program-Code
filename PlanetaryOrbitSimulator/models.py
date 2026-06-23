from django.db import models

class SimulationImage(models.Model):
    simImage = models.ImageField(upload_to = 'simulationImages')