from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from accounts.models import Address, User
from services.models import Service, ServiceCategory

from .models import Booking, BookingAttachment, RescheduleRequest
from .utils import validate_provider_slot


class BookingForm(forms.ModelForm):
    GUEST_FIELDS = (
        "guest_first_name",
        "guest_last_name",
        "guest_email",
        "guest_phone",
        "guest_city",
        "guest_street",
        "guest_address_details",
    )

    category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.none(),
        required=False,
        label="Categorie",
    )
    service_query = forms.CharField(
        required=False,
        max_length=150,
        label="Tip de ajutor (scrie sau alege)",
        help_text="Exemplu: ajutor la cumparaturi, insotire la medic, mutat obiecte usoare",
    )
    saved_address = forms.ModelChoiceField(
        queryset=Address.objects.none(),
        required=False,
        label="Adresa salvata (optional)",
    )
    address_city = forms.CharField(required=False, max_length=128, label="Oras")
    address_line = forms.CharField(
        required=False, max_length=255, label="Adresa (strada, numar, bloc)"
    )
    address_details = forms.CharField(
        required=False,
        max_length=255,
        label="Detalii adresa (optional)",
    )

    guest_first_name = forms.CharField(required=False, max_length=150, label="Prenume")
    guest_last_name = forms.CharField(required=False, max_length=150, label="Nume")
    guest_email = forms.EmailField(required=False, label="Email")
    guest_phone = forms.CharField(required=False, max_length=32, label="Telefon")
    guest_city = forms.CharField(required=False, max_length=128, label="Oras")
    guest_street = forms.CharField(required=False, max_length=255, label="Strada")
    guest_address_details = forms.CharField(
        required=False,
        max_length=255,
        label="Detalii adresa (optional)",
    )

    scheduled_start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    provider = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Alege voluntar (optional)",
    )

    class Meta:
        model = Booking
        fields = [
            "service",
            "provider",
            "description",
            "is_urgent",
            "urgency_level",
            "scheduled_start",
            "duration_minutes",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.user = user if getattr(user, "is_authenticated", False) else None
        services_qs = Service.objects.filter(is_active=True).select_related("category")
        categories_qs = ServiceCategory.objects.filter(is_active=True).order_by("name")
        self.fields["category"].queryset = categories_qs
        self.fields["category"].help_text = (
            "Alege mai intai categoria, ca sa restrangem tipurile de ajutor."
        )
        self.fields["service"].queryset = services_qs
        self.fields["service"].required = False
        self.fields["service"].empty_label = "Alege tipul de ajutor din lista"
        self.fields["service"].help_text = (
            "Daca stii exact ce iti trebuie, poti selecta direct din lista."
        )
        self.fields["service_query"].widget.attrs.update(
            {
                "list": "service-suggestions",
                "placeholder": "Scrie tipul de ajutor dorit",
                "autocomplete": "off",
            }
        )
        self.fields["description"].label = "Descrie pe scurt ce ai nevoie"
        self.fields["description"].widget.attrs.update(
            {"rows": 4, "placeholder": "Ex: scurgere la chiuveta in bucatarie"}
        )
        self.fields["scheduled_start"].label = "Cand ai nevoie de ajutor?"
        self.fields["scheduled_start"].help_text = (
            "Alege un interval realist, ca sa gasim mai usor un voluntar disponibil."
        )
        self.fields["duration_minutes"].label = "Durata estimata (minute)"
        self.fields["duration_minutes"].help_text = (
            "Ne ajuta sa evitam suprapuneri si sa gasim voluntarul potrivit."
        )
        self.fields["provider"].help_text = "Lasa gol daca vrei asignare automata."
        self.fields["saved_address"].empty_label = "Scriu o adresa noua"
        self.fields["saved_address"].help_text = (
            "Selecteaza o adresa salvata sau completeaza manual campurile de mai jos."
        )
        self.fields["address_city"].help_text = (
            "Orasul este folosit pentru filtrarea voluntarilor disponibili."
        )
        self.fields["address_line"].help_text = (
            "Include strada, numarul si orice reper important."
        )
        self.fields["address_details"].help_text = (
            "Optional: bloc, etaj, apartament, interfon sau alte indicii utile."
        )
        self.fields["urgency_level"].label = "Nivel de urgenta"
        self.fields["urgency_level"].help_text = (
            "Foloseste urgent doar cand cererea chiar are nevoie de reactie rapida."
        )
        self.fields["is_urgent"].label = "Marcheaza ca urgent"
        self.fields["is_urgent"].help_text = (
            "Bifeaza doar daca este nevoie de ajutor intr-un interval scurt."
        )
        self.fields["guest_first_name"].help_text = (
            "Il folosim pentru confirmari si pentru chatul asociat cererii."
        )
        self.fields["guest_email"].help_text = (
            "Daca nu ai cont, il folosim pentru a crea automat accesul la cerere."
        )
        self.fields["guest_phone"].help_text = (
            "Ajuta la coordonarea rapida daca cererea este acceptata."
        )

        self.service_suggestions = list(
            services_qs.values("id", "name", "category_id", "category__name")
        )
        self.fields["provider"].queryset = (
            User.objects.filter(
                role=User.Roles.PROVIDER,
                provider_profile__verification_status="verified",
            )
            .order_by("first_name", "last_name")
            .distinct()
        )
        if self.user:
            addresses_qs = Address.objects.filter(user=self.user).order_by(
                "-is_default", "-created_at"
            )
            self.fields["saved_address"].queryset = addresses_qs
            for field_name in self.GUEST_FIELDS:
                self.fields.pop(field_name, None)
            self.order_fields(
                [
                    "category",
                    "service_query",
                    "service",
                    "provider",
                    "description",
                    "saved_address",
                    "address_city",
                    "address_line",
                    "address_details",
                    "is_urgent",
                    "urgency_level",
                    "scheduled_start",
                    "duration_minutes",
                ]
            )
            return

        self.fields.pop("saved_address", None)
        self.fields["guest_first_name"].required = True
        self.fields["guest_email"].required = True
        self.fields["guest_phone"].required = True
        self.fields["guest_city"].required = False
        self.fields["guest_street"].required = False
        self.order_fields(
            [
                "guest_first_name",
                "guest_last_name",
                "guest_email",
                "guest_phone",
                "guest_city",
                "guest_street",
                "guest_address_details",
                "category",
                "service_query",
                "service",
                "provider",
                "description",
                "address_city",
                "address_line",
                "address_details",
                "is_urgent",
                "urgency_level",
                "scheduled_start",
                "duration_minutes",
            ]
        )

    def clean_guest_email(self):
        email = self.cleaned_data.get("guest_email")
        if self.user or not email:
            return email
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Exista deja un cont cu acest email. Autentifica-te pentru a continua."
            )
        return email

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        service = cleaned.get("service")
        service_query = (cleaned.get("service_query") or "").strip()

        if service_query:
            qs = Service.objects.filter(is_active=True)
            if category:
                qs = qs.filter(category=category)
            match = qs.filter(name__iexact=service_query).first()
            if not match:
                match = qs.filter(name__icontains=service_query).order_by("name").first()
            if match:
                service = match
                cleaned["service"] = match
            else:
                self.add_error(
                    "service_query",
                    "Serviciul nu exista in categoriile curente. Selecteaza din lista.",
                )

        if not service:
            self.add_error("service", "Alege un serviciu din lista.")
            return cleaned

        if category and service.category_id != category.id:
            self.add_error("service", "Serviciul selectat nu apartine categoriei alese.")

        if self.user:
            selected = cleaned.get("saved_address")
            city = (cleaned.get("address_city") or "").strip()
            line = (cleaned.get("address_line") or "").strip()
            if not selected and not city:
                self.add_error(
                    "address_city",
                    "Completeaza orasul sau selecteaza o adresa salvata.",
                )
            if not selected and not line:
                self.add_error(
                    "address_line",
                    "Completeaza adresa sau selecteaza o adresa salvata.",
                )
            if selected:
                cleaned["resolved_address"] = selected
        else:
            guest_city = (cleaned.get("guest_city") or "").strip()
            guest_street = (cleaned.get("guest_street") or "").strip()
            typed_city = (cleaned.get("address_city") or "").strip()
            typed_line = (cleaned.get("address_line") or "").strip()
            if not (guest_city or typed_city):
                self.add_error("address_city", "Completeaza orasul.")
            if not (guest_street or typed_line):
                self.add_error("address_line", "Completeaza adresa.")

        start = cleaned.get("scheduled_start")
        duration = cleaned.get("duration_minutes") or 0
        provider = cleaned.get("provider")
        if not start or not provider:
            return cleaned

        try:
            validate_provider_slot(
                provider, start, duration, booking=self.instance
            )
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc)
        return cleaned


class RescheduleRequestForm(forms.Form):
    scheduled_start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        label="Noua data si ora",
        help_text="Alege un interval viitor care functioneaza pentru ambele parti.",
    )
    duration_minutes = forms.IntegerField(
        min_value=15,
        initial=60,
        label="Durata estimata (minute)",
        help_text="Pastreaza durata realista ca sa evitam suprapuneri.",
    )
    note = forms.CharField(
        required=False,
        max_length=255,
        label="Nota pentru celalalt utilizator",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Explica pe scurt de ce propui schimbarea sau ce trebuie retinut.",
    )

    def __init__(self, booking, user, *args, **kwargs):
        self.booking = booking
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("scheduled_start")
        duration = cleaned.get("duration_minutes") or 0
        if not start:
            return cleaned

        if start < timezone.now():
            raise forms.ValidationError("Alege un interval din viitor.")

        if self.booking.reschedule_requests.filter(
            status=RescheduleRequest.Status.PENDING
        ).exists():
            raise forms.ValidationError(
                "Exista deja o solicitare de reprogramare in asteptare."
            )

        if self.booking.provider:
            try:
                validate_provider_slot(
                    self.booking.provider, start, duration, booking=self.booking
                )
            except DjangoValidationError as exc:
                raise forms.ValidationError(exc)
        return cleaned


class CancelBookingForm(forms.Form):
    reason = forms.CharField(
        required=False,
        max_length=255,
        label="Motiv (optional)",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Ajuta-l pe celalalt utilizator sa inteleaga de ce se inchide cererea.",
    )


class CompleteBookingForm(forms.Form):
    note = forms.CharField(
        required=False,
        max_length=255,
        label="Nota pentru client",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Rezuma ce ai facut sau ce ar trebui verificat inainte de confirmare.",
    )


class ResolveDisputeForm(forms.Form):
    resolution_note = forms.CharField(
        required=False,
        max_length=255,
        label="Rezolvare (nota)",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Noteaza clar ce s-a lamurit si de ce disputa poate fi inchisa.",
    )


class DisputeMessageForm(forms.Form):
    text = forms.CharField(
        label="Mesaj",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    attachment = forms.FileField(required=False, label="Atasament (optional)")


class BookingRepeatForm(forms.Form):
    scheduled_start = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        label="Data & ora",
        help_text="Daca il lasi gol, noua rezervare porneste din momentul curent.",
    )
    duration_minutes = forms.IntegerField(
        required=False,
        min_value=15,
        label="Durata (minute)",
        help_text="Poti ajusta durata fara sa refaci toata cererea.",
    )


class BookingAttachmentForm(forms.ModelForm):
    class Meta:
        model = BookingAttachment
        fields = ["file", "note"]
        labels = {
            "file": "Fisier",
            "note": "Nota (optional)",
        }
        help_texts = {
            "file": "Incarca un document, o poza sau un alt fisier relevant pentru comanda.",
            "note": "Adauga un context scurt ca sa se inteleaga ce contine fisierul.",
        }


class RecurringBookingForm(forms.Form):
    service = forms.ModelChoiceField(queryset=Service.objects.none(), label="Serviciu")
    provider = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Roles.PROVIDER),
        required=False,
        label="Prestator (optional)",
    )
    address = forms.ModelChoiceField(queryset=Address.objects.none(), label="Adresa")
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Descriere",
    )
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    duration_minutes = forms.IntegerField(min_value=15, initial=60)
    frequency = forms.ChoiceField(
        choices=[
            ("weekly", "Saptamanal"),
            ("biweekly", "Bilunar"),
            ("monthly", "Lunar"),
        ]
    )
    occurrences = forms.IntegerField(min_value=1, max_value=26, initial=4)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        self.fields["address"].queryset = Address.objects.filter(user=user)
        self.fields["service"].help_text = (
            "Alege serviciul pe care vrei sa-l programezi repetat."
        )
        self.fields["provider"].help_text = "Lasa gol daca vrei asignare ulterioara."
        self.fields["address"].help_text = (
            "Folosim una dintre adresele deja salvate in cont."
        )
        self.fields["description"].help_text = (
            "Optional: mentiuni care se aplica fiecarei aparitii."
        )
        self.fields["start_date"].label = "Data primei rezervari"
        self.fields["start_date"].help_text = "De aici porneste intreaga serie."
        self.fields["start_time"].label = "Ora de start"
        self.fields["start_time"].help_text = (
            "Toate aparitiile folosesc aceeasi ora."
        )
        self.fields["duration_minutes"].label = "Durata (minute)"
        self.fields["duration_minutes"].help_text = (
            "Stabileste o durata realista pentru fiecare aparitie."
        )
        self.fields["frequency"].label = "Frecventa"
        self.fields["frequency"].help_text = (
            "Alege cat de des se repeta rezervarea."
        )
        self.fields["occurrences"].label = "Numar de aparitii"
        self.fields["occurrences"].help_text = (
            "Poti crea pana la 26 de aparitii dintr-un foc."
        )
