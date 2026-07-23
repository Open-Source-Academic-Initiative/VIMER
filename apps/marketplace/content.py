import mimetypes
from pathlib import Path
from uuid import uuid4

import bleach
import markdown
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify


ALLOWED_ATTACHMENT_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}

# Magic bytes por tipo permitido: el tipo real se determina del contenido del
# archivo, nunca del Content-Type que declara el navegador (falsificable).
ATTACHMENT_SIGNATURES = (
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)

MARKDOWN_ALLOWED_TAGS = {
    "p",
    "br",
    "h1",
    "h2",
    "h3",
    "ul",
    "ol",
    "li",
    "blockquote",
    "em",
    "strong",
    "code",
    "pre",
    "a",
}
MARKDOWN_ALLOWED_ATTRIBUTES = {"a": ["href", "title"]}
MARKDOWN_ALLOWED_PROTOCOLS = {"http", "https", "mailto"}


def render_markdown(value: str) -> str:
    raw_html = markdown.markdown(
        value or "",
        extensions=["extra", "sane_lists"],
        output_format="html",
    )
    return bleach.clean(
        raw_html,
        tags=MARKDOWN_ALLOWED_TAGS,
        attributes=MARKDOWN_ALLOWED_ATTRIBUTES,
        protocols=MARKDOWN_ALLOWED_PROTOCOLS,
        strip=True,
    )


def sniff_attachment_content_type(uploaded_file) -> str:
    """Return the real MIME type of the file from its magic bytes, or ""."""
    head = uploaded_file.read(8)
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    for signature, content_type in ATTACHMENT_SIGNATURES:
        if head.startswith(signature):
            return content_type
    return ""


def validate_attachment_file(uploaded_file) -> None:
    if not uploaded_file:
        return

    max_bytes = settings.MARKETPLACE_ATTACHMENT_MAX_BYTES
    if uploaded_file.size > max_bytes:
        raise ValidationError(
            f"El archivo no puede superar {max_bytes // (1024 * 1024)} MB."
        )

    sniffed_type = sniff_attachment_content_type(uploaded_file)
    if sniffed_type not in ALLOWED_ATTACHMENT_MIME_TYPES:
        raise ValidationError("Solo se permiten archivos PDF, JPG o PNG.")

    guessed_type, _ = mimetypes.guess_type(uploaded_file.name)
    if guessed_type and guessed_type != sniffed_type:
        raise ValidationError("La extension del archivo no coincide con su tipo.")


def build_attachment_upload_path(instance, filename: str) -> str:
    extension = ALLOWED_ATTACHMENT_MIME_TYPES.get(
        getattr(instance, "content_type", ""),
        "",
    )
    if not extension:
        extension = Path(filename).suffix
    basename = slugify(filename.rsplit(".", 1)[0]) or "adjunto"
    return f"marketplace/attachments/{instance.opaque_id}/{basename}{extension}"


def build_application_summary(
    *,
    problem_understanding: str,
    proposed_solution: str,
    capabilities_evidence: str,
    execution_plan: str,
) -> str:
    return "\n\n".join(
        [
            f"Entendimiento del problema: {(problem_understanding or '').strip()}",
            f"Solución propuesta: {(proposed_solution or '').strip()}",
            f"Capacidades y evidencia: {(capabilities_evidence or '').strip()}",
            f"Plan de ejecución: {(execution_plan or '').strip()}",
        ]
    )


def new_opaque_id() -> str:
    return uuid4().hex
