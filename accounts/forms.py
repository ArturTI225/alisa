from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Address, NotificationPreference, User


class SignupForm(UserCreationForm):
    FIELD_COPY = {
        "username": (
            "Nume utilizator",
            "Il folosesti la autentificare si in zonele interne ale demo-ului.",
        ),
        "email": (
            "Email",
            "Primeste aici actualizari importante despre rezervari si cont.",
        ),
        "first_name": (
            "Prenume",
            "Apare in profil si in conversatii.",
        ),
        "last_name": (
            "Nume",
            "Te ajuta sa fii recunoscut in rezervari si notificari.",
        ),
        "phone": (
            "Telefon",
            "Optional acum, dar util pentru coordonarea unei rezervari.",
        ),
        "city": (
            "Oras",
            "Ne ajuta sa-ti aratam cererile si prestatorii relevanti.",
        ),
        "password1": (
            "Parola",
            "Alege o parola puternica, folosita doar pentru acest demo.",
        ),
        "password2": (
            "Confirma parola",
            "Repeta parola pentru a evita blocajele la prima autentificare.",
        ),
    }

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            label, help_text = self.FIELD_COPY.get(
                name, (field.label, field.help_text)
            )
            field.label = label
            field.help_text = help_text

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
    FIELD_COPY = {
        "booking_updates": (
            "Actualizari pentru rezervari",
            "Primeste mesaje cand o rezervare este acceptata, schimbata sau inchisa.",
        ),
        "disputes": (
            "Dispute si rezolvari",
            "Afla imediat cand apare sau se inchide o disputa.",
        ),
        "recurring": (
            "Rezervari recurente",
            "Vezi noutati legate de seriile recurente si urmatoarele aparitii.",
        ),
        "chat_messages": (
            "Mesaje noi in chat",
            "Notificari pentru conversatiile active din platforma.",
        ),
        "bids": (
            "Aplicatii si raspunsuri",
            "Mesaje despre aplicatii noi si deciziile luate pe ele.",
        ),
        "urgent_ads": (
            "Cereri urgente din apropiere",
            "Actualizari rapide pentru anunturi sau cereri marcate ca urgente.",
        ),
        "reviews": (
            "Review-uri",
            "Afla cand primesti un review sau cand apare un pas nou in fluxul de evaluare.",
        ),
        "marketing": (
            "Noutati despre produs",
            "Mesaje ocazionale despre imbunatatiri si schimbari utile din demo.",
        ),
        "in_app_sound": (
            "Sunet pentru notificarile live",
            "Reda un semnal scurt cand primesti o notificare noua in browser. Implicit este oprit.",
        ),
    }

    class Meta:
        model = NotificationPreference
        fields = [
            "booking_updates",
            "disputes",
            "recurring",
            "chat_messages",
            "bids",
            "urgent_ads",
            "reviews",
            "marketing",
            "in_app_sound",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            label, help_text = self.FIELD_COPY.get(
                name, (field.label, field.help_text)
            )
            field.label = label
            field.help_text = help_text
