"""
URL configuration for PlanetaryOrbitSimulator project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve
from django.conf import settings

from PlanetaryOrbitSimulator import views

urlpatterns = [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    path('admin/', admin.site.urls),
    path('settings/', views.settingsPage),
    path('create/', views.createPage),
    path('create/<int:templateIndex>', views.createPage),
    path('load/', views.loadingPage),
    path('load/<int:saveIndex>', views.loadingPage),
    path('run/<int:startSimulation>/<int:autoRunSimulation>', views.runSimulation),
    path('autoRun/<int:autoRunSimulation>/<int:reverseSimulation>', views.switchRun),
    path('run/<int:startSimulation>/<int:autoRunSimulation>/<int:reverseSimulation>', views.runSimulation),
    path('edit/<int:selectedBody>', views.editSimulationPage),
    path('login/', views.loginPage),
    path('register/', views.registerPage),

    path('', views.homePage)
]
