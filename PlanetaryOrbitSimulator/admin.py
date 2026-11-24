from django.contrib import admin

from PlanetaryOrbitSimulator.models import StoredSimulation, UserProfile

admin.site.register(StoredSimulation)
admin.site.register(UserProfile)