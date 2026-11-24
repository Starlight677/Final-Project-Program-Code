import matplotlib.colors as mcolors
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class SimulationNameForm(forms.Form):
    """Form for configuring simulation metadata, viewport size, and focus."""

    simulationName = forms.CharField(label="Simulation Save Name", max_length=100, required=False)
    simulationSize = forms.FloatField(label="View Window Size (AU)", required=False, min_value=1e-6)
    simulationTimePerUpdate = forms.FloatField(label="Days per Simulation Update", required=False, min_value=1e-4)
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
    bodyMass = forms.FloatField(label="Body Mass (kg)", required=False, min_value=0)
    bodyRadius = forms.FloatField(label="Body Radius (KM)", required=False, min_value=0)
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

    def clean_bodyColour(self):
        colour = (self.cleaned_data.get("bodyColour") or "").strip().lower()
        if colour and colour not in mcolors.CSS4_COLORS:
            raise forms.ValidationError("Invalid CSS colour name.")
        return colour


class LoginForm(forms.Form):
    username = forms.CharField(label="Username", max_length=100, required=True)
    password = forms.CharField(label="Password", max_length=100, required=True, widget=forms.PasswordInput)


class RegisterForm(LoginForm):
    passwordRepeated = forms.CharField(
        label="Repeat Password", max_length=100, required=True, widget=forms.PasswordInput
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        passwordRepeated = cleaned_data.get("passwordRepeated")

        if username and User.objects.filter(username=username).exists():
            self.add_error("username", "Username already exists.")

        if password and passwordRepeated and password != passwordRepeated:
            self.add_error("passwordRepeated", "Passwords do not match.")

        if password:
            try:
                validate_password(password, user=User(username=username) if username else None)
            except ValidationError as exc:
                self.add_error("password", exc)

        return cleaned_data
