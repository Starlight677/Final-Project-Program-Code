from django.db import models

class simulationImage(models.Model):
    simImage = models.ImageField(upload_to = 'simulationImages')