import io

from django.template.loader import render_to_string


def render_certificate_html(context):
    return render_to_string("bookings/certificate.html", context)


def generate_pdf_from_html(html: str) -> bytes:
    try:
        from weasyprint import HTML  # type: ignore
    except Exception:
        return b""
    pdf_io = io.BytesIO()
    HTML(string=html).write_pdf(target=pdf_io)
    return pdf_io.getvalue()
