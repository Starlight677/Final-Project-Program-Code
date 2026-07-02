from django import forms

class SimulationNameForm(forms.Form):
    simulationName = forms.CharField(label="Simulation Name", max_length=100, required=False)