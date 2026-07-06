from django import forms

class SimulationNameForm(forms.Form):
    # Used for editing the simulation during creation
    simulationName = forms.CharField(label="Simulation Save Name", max_length=100, required=False)
    simulationSize = forms.FloatField(label="Simulation Size (AU)", required=False)
    simulationTimePerUpdate = forms.FloatField(label="Days per Simulation Update", required=False)

class BodyDetailsForm(forms.Form):
    # Used for editing a body in the simulation
    bodyName = forms.CharField(label="Body Name", max_length=100, required=False)
    bodyMass = forms.FloatField(label="Body Mass (kg)", required=False)
    bodyColour = forms.CharField(label="Body Colour", max_length=100, required=False)