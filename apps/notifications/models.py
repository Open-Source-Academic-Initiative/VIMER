from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Kind(models.TextChoices):
        EVALUATION_STARTED = "EVALUATION_STARTED", _("Evaluación iniciada")
        APPLICATION_EVALUATED = "APPLICATION_EVALUATED", _("Propuesta evaluada")
        CHALLENGE_AWARDED = "CHALLENGE_AWARDED", _("Desafío adjudicado")
        CHALLENGE_CLOSED = "CHALLENGE_CLOSED", _("Recepción cerrada")
        CHALLENGE_CANCELLED = "CHALLENGE_CANCELLED", _("Desafío cancelado")
        CHALLENGE_DESERTED = "CHALLENGE_DESERTED", _("Desafío desierto")
        REPRESENTATIVE_JOIN_REQUESTED = (
            "REPRESENTATIVE_JOIN_REQUESTED",
            _("Solicitud de unión creada"),
        )
        REPRESENTATIVE_JOIN_APPROVED = (
            "REPRESENTATIVE_JOIN_APPROVED",
            _("Solicitud de unión aprobada"),
        )
        REPRESENTATIVE_JOIN_REJECTED = (
            "REPRESENTATIVE_JOIN_REJECTED",
            _("Solicitud de unión rechazada"),
        )
        REPRESENTATIVE_JOIN_EXPIRED = (
            "REPRESENTATIVE_JOIN_EXPIRED",
            _("Solicitud de unión expirada"),
        )
        ORGANIZATION_OWNERSHIP_TRANSFERRED = (
            "ORGANIZATION_OWNERSHIP_TRANSFERRED",
            _("Titularidad transferida"),
        )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(_("Tipo"), max_length=40, choices=Kind.choices)
    title = models.CharField(_("Título"), max_length=120)
    body = models.TextField(_("Mensaje"))
    link = models.CharField(_("Enlace"), max_length=255, blank=True, default="")
    read_at = models.DateTimeField(_("Leída en"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Notificación")
        verbose_name_plural = _("Notificaciones")
        ordering = ["-created_at", "-id"]

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def __str__(self):
        return f"{self.title} -> {self.recipient}"
