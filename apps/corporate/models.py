from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.corporate.avatar_utils import validate_logo_image

class Organization(models.Model):
    class MarketRole(models.TextChoices):
        DEMAND_SIDE = "DEMAND_SIDE", _("Solicitante")
        SUPPLY_SIDE = "SUPPLY_SIDE", _("Proveedor tecnológico")

    tax_id = models.CharField(_("NIT"), max_length=20, unique=True)
    business_name = models.CharField(_("Razón Social"), max_length=255)
    chamber_of_commerce_record = models.CharField(_("Registro Cámara de Comercio"), max_length=100)
    role = models.CharField(max_length=20, choices=MarketRole.choices)
    
    logo = models.ImageField(
        upload_to="corporate/logos/",
        null=True,
        blank=True,
        validators=[validate_logo_image],
    )
    description = models.TextField(_("Descripción"), blank=True)
    economic_activity = models.TextField(_("Actividad Económica"), blank=True)
    contact_email = models.EmailField(_("Email"))
    contact_phone = models.CharField(_("Teléfono"), max_length=20)

    class Meta:
        verbose_name = _("Organización")

    def __str__(self):
        return self.business_name
