from datetime import timedelta

from django.core.exceptions import ValidationError

from .models import Availability, Booking


def validate_provider_slot(provider, start, duration_minutes: int, booking=None):
    """
    Ensure the provider is free and marked available for the given slot.
    """
    if not provider or not start:
        return
    end_time = start + timedelta(minutes=duration_minutes)
    weekday = start.isoweekday()

    if provider.availability_exceptions.filter(
        date=start.date(), is_available=False
    ).exists():
        raise ValidationError("Prestatorul este indisponibil in acea zi.")

    if not Availability.objects.filter(
        provider=provider,
        weekday=weekday,
        is_active=True,
        start_time__lte=start.time(),
        end_time__gte=end_time.time(),
    ).exists():
        raise ValidationError(
            "Prestatorul nu are disponibilitate setata pentru acest interval."
        )

    overlapping = Booking.objects.filter(
        provider=provider,
        status__in=[
            Booking.Status.PENDING,
            Booking.Status.CONFIRMED,
            Booking.Status.IN_PROGRESS,
            Booking.Status.RESCHEDULE_REQUESTED,
        ],
    )
    if booking:
        overlapping = overlapping.exclude(pk=getattr(booking, "pk", None))

    for other in overlapping:
        if other.scheduled_start < end_time and other.scheduled_end > start:
            raise ValidationError(
                "Prestatorul este deja ocupat in intervalul ales."
            )


def ensure_help_request_conversation(help_request):
    """
    Ensure there is one conversation attached to a help request
    and both participants are present in the conversation.
    """
    if not help_request:
        return None

    from chat.models import Conversation

    conversation, _ = Conversation.objects.get_or_create(
        help_request=help_request
    )
    participant_ids = [
        help_request.created_by_id,
        help_request.matched_volunteer_id,
    ]
    participant_ids = [pid for pid in participant_ids if pid]
    if participant_ids:
        conversation.participants.add(*participant_ids)
    return conversation


def ensure_booking_conversation(booking):
    """
    Ensure there is one conversation attached to a booking
    and both participants are present in the conversation.
    """
    if not booking:
        return None

    from chat.models import Conversation

    conversation, _ = Conversation.objects.get_or_create(booking=booking)
    participant_ids = [booking.client_id, booking.provider_id]
    participant_ids = [pid for pid in participant_ids if pid]
    if participant_ids:
        conversation.participants.add(*participant_ids)
    return conversation
