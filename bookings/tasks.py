from celery import shared_task

from django.core.files.base import ContentFile
from .models import CompletionCertificate, HelpRequest


@shared_task
def generate_certificate(help_request_id: int):
    try:
        hr = HelpRequest.objects.select_related("matched_volunteer").get(pk=help_request_id)
    except HelpRequest.DoesNotExist:
        return
    if not hr.matched_volunteer:
        return
    certificate, created = CompletionCertificate.objects.get_or_create(
        help_request=hr,
        defaults={
            "volunteer": hr.matched_volunteer,
            "summary": hr.title,
        },
    )
    if created or not certificate.pdf:
        content = ContentFile(f"Certificate for help request {hr.pk}".encode("utf-8"))
        certificate.pdf.save(f"certificate_{hr.pk}.pdf", content, save=True)
    return certificate.pk
