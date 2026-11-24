from django import forms


class SimulationNameForm(forms.Form):
    """Form for configuring simulation metadata, viewport size, and focus."""

    simulationName = forms.CharField(label="Simulation Save Name", max_length=100, required=False)
    simulationSize = forms.FloatField(label="View Window Size (AU)", required=False)
    simulationTimePerUpdate = forms.FloatField(label="Days per Simulation Update", required=False)
    focusedBody = forms.ChoiceField(label="Focused Body", required=False)

    def __init__(self, *args, body_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if body_choices is not None:
            self.fields['focusedBody'].choices = body_choices
        else:
            del self.fields['focusedBody']


class BodyDetailsForm(forms.Form):
    """Form for editing a single celestial body's properties and orbit reference."""

    bodyName = forms.CharField(label="Body Name", max_length=100, required=False)
    bodyMass = forms.FloatField(label="Body Mass (kg)", required=False)
    bodyRadius = forms.FloatField(label="Body Radius (KM)", required=False)
    bodyColour = forms.CharField(label="Body Colour", max_length=100, required=False)
    bodyReference = forms.ChoiceField(label="Orbit Reference Body", required=False)

    bodyXPosition = forms.FloatField(label="Body X Position (AU)", required=False)
    bodyYPosition = forms.FloatField(label="Body Y Position (AU)", required=False)

    bodyXSpeed = forms.FloatField(label="Body X Velocity (KM/s)", required=False)
    bodyYSpeed = forms.FloatField(label="Body Y Velocity (KM/s)", required=False)

    def __init__(self, *args, body_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bodyReference'].choices = (
            body_choices if body_choices is not None else [(-1, "None (Static Grid)")]
        )


class LoginForm(forms.Form):
    username = forms.CharField(label="Username", max_length=100, required=True)
    password = forms.CharField(label="Password", max_length=100, required=True, widget=forms.PasswordInput)


class RegisterForm(LoginForm):
    passwordRepeated = forms.CharField(
        label="Repeat Password", max_length=100, required=True, widget=forms.PasswordInput
    )
