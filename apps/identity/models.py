from uuid import uuid4

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def new_email_verification_token() -> str:
    return uuid4().hex


class User(AbstractUser):
    """
    Custom user model for VIMER.
    Represents the human operator acting on behalf of an organization.
    """
    class AccountStatus(models.TextChoices):
        ACTIVE = "ACTIVE", _("Activo")
        PENDING_APPROVAL = "PENDING_APPROVAL", _("Pendiente de aprobación")
        INACTIVE = "INACTIVE", _("Inactivo")

    email = models.EmailField(_("email address"), unique=True)
    organization = models.ForeignKey(
        'corporate.Organization', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="members"
    )
    status = models.CharField(
        _("Estado de cuenta"),
        max_length=24,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )
    is_organization_titular = models.BooleanField(
        _("Representante titular"),
        default=False,
    )
    is_email_verified = models.BooleanField(
        _("Correo verificado"),
        default=False,
    )
    accepted_terms_version = models.CharField(
        _("Versión de términos aceptada"),
        max_length=24,
        blank=True,
        default="",
    )
    accepted_privacy_policy_version = models.CharField(
        _("Versión de política aceptada"),
        max_length=24,
        blank=True,
        default="",
    )

    class Meta:
        verbose_name = _("usuario")
        verbose_name_plural = _("usuarios")
        constraints = [
            models.UniqueConstraint(
                fields=["organization"],
                condition=Q(is_organization_titular=True, status="ACTIVE"),
                name="unique_active_titular_per_organization",
            ),
        ]

    @property
    def can_operate(self) -> bool:
        return self.status == self.AccountStatus.ACTIVE and self.is_email_verified

    def __str__(self):
        role_label = f" [{self.organization.role}]" if self.organization else ""
        return f"{self.username} ({self.email}){role_label}"


class OrganizationJoinRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pendiente")
        APPROVED = "APPROVED", _("Aprobada")
        REJECTED = "REJECTED", _("Rechazada")
        EXPIRED = "EXPIRED", _("Expirada")

    organization = models.ForeignKey(
        "corporate.Organization",
        on_delete=models.CASCADE,
        related_name="join_requests",
    )
    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="organization_join_requests",
    )
    status = models.CharField(
        _("Estado"),
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    decided_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="decided_organization_join_requests",
        null=True,
        blank=True,
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Solicitud de unión a organización")
        verbose_name_plural = _("Solicitudes de unión a organización")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "requester"],
                condition=Q(status="PENDING"),
                name="unique_pending_join_request_per_user_and_organization",
            ),
        ]

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    def mark_approved(self, *, actor: User) -> None:
        self.status = self.Status.APPROVED
        self.decided_by = actor
        self.decided_at = timezone.now()
        self.requester.status = User.AccountStatus.ACTIVE
        self.requester.save(update_fields=["status"])
        self.save(update_fields=["status", "decided_by", "decided_at"])

    def mark_rejected(self, *, actor: User) -> None:
        self.status = self.Status.REJECTED
        self.decided_by = actor
        self.decided_at = timezone.now()
        self.requester.status = User.AccountStatus.INACTIVE
        self.requester.save(update_fields=["status"])
        self.save(update_fields=["status", "decided_by", "decided_at"])

    def __str__(self):
        return f"{self.requester} -> {self.organization} ({self.status})"


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token = models.CharField(max_length=64, unique=True, default=new_email_verification_token)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Token de verificación de correo")
        verbose_name_plural = _("Tokens de verificación de correo")
        ordering = ["-created_at"]

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and self.expires_at >= timezone.now()

    def mark_used(self) -> None:
        self.used_at = timezone.now()
        self.user.is_email_verified = True
        self.user.save(update_fields=["is_email_verified"])
        self.save(update_fields=["used_at"])
