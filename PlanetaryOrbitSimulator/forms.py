from django import forms

class SimulationNameForm(forms.Form):
    simulationName = forms.CharField(label="Simulation Save Name", max_length=100, required=False)
    simulationSize = forms.FloatField(label="Simulation Size (AU)", required=False)
    simulationTimePerUpdate = forms.FloatField(label="Days per Simulation Update", required=False)