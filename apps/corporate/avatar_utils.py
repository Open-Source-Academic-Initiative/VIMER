from __future__ import annotations

from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

ALLOWED_IMAGE_FORMATS = {"PNG", "JPEG"}


def validate_logo_image(uploaded_file) -> None:
    if not uploaded_file:
        return

    try:
        image = Image.open(uploaded_file)
        image.verify()
        image_format = (image.format or "").upper()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("Debes subir una imagen valida en formato PNG o JPG.") from exc
    finally:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Solo se permiten imagenes PNG o JPG.")


def generate_default_logo(*, business_name: str, tax_id: str) -> ContentFile:
    initials = _build_initials(business_name)
    background = _pick_background_color(f"{business_name}:{tax_id}")
    image = Image.new("RGB", (256, 256), background)
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 110)
    except OSError:
        font = ImageFont.load_default()

    text_box = draw.textbbox((0, 0), initials, font=font)
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    position = ((256 - text_width) / 2, (256 - text_height) / 2 - 8)
    draw.text(position, initials, fill="white", font=font)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    filename_root = slugify(business_name) or "organization"
    filename = f"{filename_root}-{slugify(tax_id) or 'logo'}.png"
    return ContentFile(buffer.getvalue(), name=filename)


def _build_initials(business_name: str) -> str:
    tokens = [token[0].upper() for token in business_name.split() if token]
    return "".join(tokens[:2]) or "V"


def _pick_background_color(seed: str) -> tuple[int, int, int]:
    digest = seed.encode("utf-8")
    red = 40 + (sum(digest[::3]) % 150)
    green = 40 + (sum(digest[1::3]) % 150)
    blue = 40 + (sum(digest[2::3]) % 150)
    return red, green, blue
