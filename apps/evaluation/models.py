from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.marketplace.models import Application, Challenge


class AwardDecision(models.Model):
    challenge = models.OneToOneField(
        Challenge,
        on_delete=models.CASCADE,
        related_name="award_decision",
    )
    winning_application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="award_decisions",
    )
    comment = models.TextField(_("Comentario de adjudicación"))
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="award_decisions",
    )
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Decisión de adjudicación")
        verbose_name_plural = _("Decisiones de adjudicación")
        ordering = ["-decided_at"]

    def clean(self):
        errors = {}

        if self.winning_application_id and self.challenge_id:
            if self.winning_application.challenge_id != self.challenge_id:
                errors["winning_application"] = _(
                    "La propuesta seleccionada debe pertenecer al mismo desafío."
                )

        if not (self.comment or "").strip():
            errors["comment"] = _("Debes registrar un comentario de adjudicación.")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Adjudicación de {self.challenge}"
