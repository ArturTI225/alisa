import logging

from celery import shared_task

from django.core.files.base import ContentFile

from config.observability import bind_log_context

from .models import CompletionCertificate, HelpRequest


logger = logging.getLogger("platform.tasks")


@shared_task
def generate_certificate(help_request_id: int, request_id: str = ""):
    with bind_log_context(
        request_id=(request_id or "-"),
        method="TASK",
        path=f"bookings.tasks.generate_certificate:{help_request_id}",
        user_id="-",
        view_name="task:generate_certificate",
    ):
        logger.info("task.started")
        try:
            hr = HelpRequest.objects.select_related("matched_volunteer").get(pk=help_request_id)
        except HelpRequest.DoesNotExist:
            logger.warning("task.skipped help_request_missing")
            return
        if not hr.matched_volunteer:
            logger.warning("task.skipped matched_volunteer_missing")
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
        logger.info("task.completed", extra={"status_code": 200, "duration_ms": "-"})
        return certificate.pk
