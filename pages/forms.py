from django import forms
from django.db.models import Q

from bookings.models import Booking
from bookings.models import HelpRequest
from services.models import ServiceCategory


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        if data:
            return [single_clean(data, initial)]
        return []


class ClientHelpRequestForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.none(),
        label="Categoria lucrarii",
    )
    description = forms.CharField(
        label="Ce s-a intamplat (scurt)",
        min_length=10,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Descrie pe scurt problema..."}),
    )
    urgency = forms.ChoiceField(
        choices=HelpRequest.Urgency.choices,
        initial=HelpRequest.Urgency.MEDIUM,
        label="Cat de critic este",
    )
    city = forms.CharField(required=False, max_length=120, label="Oras")
    region = forms.CharField(required=False, max_length=120, label="Zona")
    media = MultipleFileField(
        required=False,
        label="Foto / video",
        widget=MultipleFileInput(
            attrs={
                "multiple": True,
                "accept": "image/jpeg,image/png,video/mp4,video/webm,video/quicktime",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ServiceCategory.objects.filter(
            is_active=True
        )
        if user:
            self.fields["city"].initial = getattr(user, "city", "")


class WorkerRequestSearchForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.none(),
        required=False,
        label="Domeniu",
        empty_label="Toate domeniile",
    )
    urgency = forms.ChoiceField(
        required=False,
        label="Urgenta",
        choices=[
            ("", "Toate"),
            (HelpRequest.Urgency.LOW, "Low"),
            (HelpRequest.Urgency.MEDIUM, "Medium"),
            (HelpRequest.Urgency.HIGH, "High"),
        ],
    )
    city = forms.CharField(required=False, max_length=120, label="Oras")
    q = forms.CharField(required=False, max_length=120, label="Cauta")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ServiceCategory.objects.filter(
            is_active=True
        )


class ReviewComposeForm(forms.Form):
    booking = forms.ModelChoiceField(
        queryset=Booking.objects.none(),
        label="Rezervare finalizata",
        empty_label="Alege rezervarea",
    )
    rating = forms.IntegerField(min_value=1, max_value=5, initial=5, label="Rating")
    comment = forms.CharField(
        required=False,
        label="Comentariu",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Cum a decurs ajutorul? Ce ai apreciat?",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is None:
            return

        participated_completed = Booking.objects.filter(
            status=Booking.Status.COMPLETED,
        ).filter(
            Q(client=user) | Q(provider=user)
        )
        already_reviewed = user.reviews_authored.values_list("booking_id", flat=True)
        self.fields["booking"].queryset = (
            participated_completed.exclude(id__in=already_reviewed)
            .select_related("client", "provider", "service")
            .order_by("-completed_at", "-id")
        )
