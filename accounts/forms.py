from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Address, NotificationPreference, User


class SignupForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            (User.Roles.CLIENT, "Client"),
            (User.Roles.PROVIDER, "Worker"),
        ],
        label="Tip cont",
        widget=forms.RadioSelect(attrs={"class": "role-choice__input"}),
    )
    phone = forms.CharField(required=False, label="Telefon")
    city = forms.CharField(required=False, label="Oras")

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

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Exista deja un cont cu acest email.")
        return email


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
