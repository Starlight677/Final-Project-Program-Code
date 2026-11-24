"""URL configuration for PlanetaryOrbitSimulator project."""

from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from PlanetaryOrbitSimulator import views

urlpatterns = [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    path('admin/', admin.site.urls),

    path('', views.homePage, name='home'),
    path('login/', views.loginPage, name='login'),
    path('register/', views.registerPage, name='register'),

    path('settings/', views.settingsPage, name='settings'),

    path('create/', views.createPage, name='create'),
    path('create/<int:templateIndex>/', views.createPage, name='create_template'),
    path('load/', views.loadingPage, name='load'),
    path('load/<int:saveIndex>/', views.loadingPage, name='load_save'),

    path('run/<int:dontRunSimulation>/', views.runSimulation, name='run'),
    path('runForm/', views.processRunForm, name='run_form'),
    path('runForm/<int:isCreating>/', views.processRunForm, name='run_form_creating'),
    path('edit/<int:selectedBody>/', views.editSimulationPage, name='edit'),
    path('editForm/<int:selectedBody>/', views.processEditForm, name='edit_form'),
    path('focus/', views.changeSimulationFocus, name='focus'),
    path('update/', views.updateSimulationImage, name='update'),
    path('update/<int:reverseSimulation>/', views.updateSimulationImage, name='update_direction'),
    path('save/', views.saveSimulation, name='save'),
    path('sim-image/', views.simulationImage, name='sim_image'),
]
