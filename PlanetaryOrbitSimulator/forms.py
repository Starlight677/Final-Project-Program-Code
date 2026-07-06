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
    bodyRadius = forms.FloatField(label="Body Radius (M)", required=False)
    bodyColour = forms.CharField(label="Body Colour", max_length=100, required=False)

    bodyXPosition = forms.FloatField(label="Body X Position (M)", required=False)
    bodyYPosition = forms.FloatField(label="Body Y Position (M)", required=False)

    bodyXSpeed = forms.FloatField(label="Body X Velocity (M/s)", required=False)
    bodyYSpeed = forms.FloatField(label="Body Y Velocity (M/s)", required=False)