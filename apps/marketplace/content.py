import mimetypes
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


def validate_attachment_file(uploaded_file) -> None:
    if not uploaded_file:
        return

    max_bytes = settings.MARKETPLACE_ATTACHMENT_MAX_BYTES
    if uploaded_file.size > max_bytes:
        raise ValidationError(
            f"El archivo no puede superar {max_bytes // (1024 * 1024)} MB."
        )

    content_type = getattr(uploaded_file, "content_type", "") or ""
    guessed_type, _ = mimetypes.guess_type(uploaded_file.name)
    if not content_type:
        content_type = guessed_type or ""
    allowed_extension = ALLOWED_ATTACHMENT_MIME_TYPES.get(content_type)
    if allowed_extension is None:
        raise ValidationError("Solo se permiten archivos PDF, JPG o PNG.")

    if guessed_type and guessed_type != content_type:
        raise ValidationError("La extension del archivo no coincide con su tipo.")


def build_attachment_upload_path(instance, filename: str) -> str:
    extension = ALLOWED_ATTACHMENT_MIME_TYPES.get(
        getattr(instance, "content_type", ""),
        "",
    )
    if not extension:
        _, extension = mimetypes.guess_type(filename)
        extension = extension or ""
    basename = slugify(filename.rsplit(".", 1)[0]) or "adjunto"
    return f"marketplace/attachments/{instance.opaque_id}/{basename}{extension}"


def new_opaque_id() -> str:
    return uuid4().hex
