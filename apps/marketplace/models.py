from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.corporate.models import Organization

class Challenge(models.Model):
    """
    R&D&I challenge published by a demand-side organization.
    """
    publisher = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="published_challenges",
        limit_choices_to={'role': Organization.MarketRole.DEMAND_SIDE}
    )
    title = models.CharField(_("Título del Desafío"), max_length=255)
    description = models.TextField(_("Descripción del Reto / Necesidad"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Desafío")
        verbose_name_plural = _("Desafíos")
        ordering = ['-created_at']

    def clean(self):
        if self.publisher and self.publisher.role != Organization.MarketRole.DEMAND_SIDE:
            raise ValidationError(_("Solo las organizaciones con rol Demandante pueden publicar desafíos."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Application(models.Model):
    """
    Proposal submitted by a supply-side organization for a challenge.
    """
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="applications"
    )
    applicant = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="submitted_proposals",
        limit_choices_to={'role': Organization.MarketRole.SUPPLY_SIDE}
    )
    proposal_text = models.TextField(_("Propuesta Tecnológica / Solución"))
    
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Postulación")
        verbose_name_plural = _("Postulaciones")
        unique_together = ('challenge', 'applicant')

    def clean(self):
        if self.applicant and self.applicant.role != Organization.MarketRole.SUPPLY_SIDE:
            raise ValidationError(_("Solo las organizaciones con rol Oferente pueden aplicar a desafíos."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Propuesta de {self.applicant} para {self.challenge}"
