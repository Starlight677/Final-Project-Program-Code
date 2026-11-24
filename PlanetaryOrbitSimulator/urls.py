"""URL configuration for PlanetaryOrbitSimulator project."""

from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from PlanetaryOrbitSimulator import views

urlpatterns = [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    path('admin/', admin.site.urls),

    path('', views.homePage),
    path('login/', views.loginPage),
    path('register/', views.registerPage),

    path('settings/', views.settingsPage),
    path('settings/<int:styleIndex>', views.settingsPage),

    path('create/', views.createPage),
    path('create/<int:templateIndex>', views.createPage),
    path('load/', views.loadingPage),
    path('load/<int:saveIndex>', views.loadingPage),

    path('run/<int:dontRunSimulation>/', views.runSimulation),
    path('runForm/', views.processRunForm),
    path('runForm/<int:isCreating>', views.processRunForm),
    path('edit/<int:selectedBody>', views.editSimulationPage),
    path('editForm/<int:selectedBody>', views.processEditForm),
    path('focus/', views.changeSimulationFocus),
    path('update/', views.updateSimulationImage, name="update"),
    path('update/<int:reverseSimulation>/', views.updateSimulationImage),
]
