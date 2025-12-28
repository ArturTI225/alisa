from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from accounts.models import Address, User
from services.models import Service
from .models import Booking, RescheduleRequest, BookingAttachment
from .utils import validate_provider_slot


class BookingForm(forms.ModelForm):
    scheduled_start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    provider = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Alege prestator (optional)",
    )

    class Meta:
        model = Booking
        fields = [
            "service",
            "provider",
            "description",
            "address",
            "is_urgent",
            "urgency_level",
            "scheduled_start",
            "duration_minutes",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        if user:
            self.fields["address"].queryset = Address.objects.filter(user=user)
            self.fields["provider"].queryset = (
                User.objects.filter(
                    role=User.Roles.PROVIDER,
                    provider_profile__verification_status="verified",
                )
                .order_by("first_name", "last_name")
                .distinct()
            )

    def clean(self):
        cleaned = super().clean()
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
    )
    duration_minutes = forms.IntegerField(
        min_value=15, initial=60, label="Durata estimata (minute)"
    )
    note = forms.CharField(
        required=False,
        max_length=255,
        label="Nota pentru celalalt utilizator",
        widget=forms.Textarea(attrs={"rows": 3}),
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
    )


class CompleteBookingForm(forms.Form):
    price_final = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        label="Preț final",
        help_text="Include materialele și manopera",
    )
    extra_costs = forms.JSONField(
        required=False,
        label="Costuri suplimentare (JSON)",
        help_text='Ex: {"materiale": 120, "deplasare": 30}',
    )
    note = forms.CharField(
        required=False,
        max_length=255,
        label="Notă pentru client",
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class ResolveDisputeForm(forms.Form):
    resolution_note = forms.CharField(
        required=False,
        max_length=255,
        label="Rezolvare (nota)",
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class DisputeMessageForm(forms.Form):
    text = forms.CharField(
        label="Mesaj",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    attachment = forms.FileField(required=False, label="Atașament (optional)")


class BookingRepeatForm(forms.Form):
    scheduled_start = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        label="Data & ora",
        help_text="Dacă îl lași gol, rezervarea pornește acum.",
    )
    duration_minutes = forms.IntegerField(
        required=False, min_value=15, label="Durată (minute)"
    )


class BookingAttachmentForm(forms.ModelForm):
    class Meta:
        model = BookingAttachment
        fields = ["file", "note"]


class RecurringBookingForm(forms.Form):
    service = forms.ModelChoiceField(queryset=Service.objects.none(), label="Serviciu")
    provider = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Roles.PROVIDER),
        required=False,
        label="Prestator (optional)",
    )
    address = forms.ModelChoiceField(queryset=Address.objects.none(), label="Adresă")
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Descriere",
    )
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    duration_minutes = forms.IntegerField(min_value=15, initial=60)
    frequency = forms.ChoiceField(choices=[("weekly", "Săptămânal"), ("biweekly", "Bilunar"), ("monthly", "Lunar")])
    occurrences = forms.IntegerField(min_value=1, max_value=26, initial=4)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        self.fields["address"].queryset = Address.objects.filter(user=user)
