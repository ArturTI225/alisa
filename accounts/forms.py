from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Address, User, NotificationPreference


class SignupForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            (User.Roles.CLIENT, "Client"),
            (User.Roles.PROVIDER, "Prestator"),
        ],
        label="Rol",
    )
    phone = forms.CharField(required=False, label="Telefon")
    city = forms.CharField(required=False, label="Oraș")

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "city",
            "role",
        ]


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "label",
            "city",
            "street",
            "details",
            "latitude",
            "longitude",
            "is_default",
        ]


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = [
            "booking_updates",
            "disputes",
            "marketing",
            "recurring",
        ]
