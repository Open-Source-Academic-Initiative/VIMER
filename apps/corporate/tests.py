from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from apps.corporate.avatar_utils import (
    MAX_LOGO_BYTES,
    normalize_logo_image,
    validate_logo_image,
)


def build_image_upload(
    *,
    name: str = "logo.jpg",
    image_format: str = "JPEG",
    size: tuple[int, int] = (800, 400),
) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, "#2689e2").save(buffer, format=image_format)
    return SimpleUploadedFile(
        name,
        buffer.getvalue(),
        content_type=f"image/{image_format.lower()}",
    )


class LogoValidationTests(SimpleTestCase):
    def test_rejects_logo_larger_than_byte_limit(self):
        upload = SimpleUploadedFile(
            "logo.png",
            b"x" * (MAX_LOGO_BYTES + 1),
            content_type="image/png",
        )

        with self.assertRaisesMessage(ValidationError, "2 MiB"):
            validate_logo_image(upload)

    def test_rejects_excessive_dimensions(self):
        upload = build_image_upload(size=(2049, 10))

        with self.assertRaisesMessage(ValidationError, "2048 pixeles"):
            validate_logo_image(upload)

    def test_normalizes_logo_to_metadata_free_bounded_png(self):
        upload = build_image_upload(name="Mi Logo.jpg", size=(1200, 600))

        normalized = normalize_logo_image(upload, filename_stem="Mi Empresa")

        self.assertEqual(normalized.name, "mi-empresa.png")
        with Image.open(normalized) as image:
            self.assertEqual(image.format, "PNG")
            self.assertLessEqual(image.width, 512)
            self.assertLessEqual(image.height, 512)
