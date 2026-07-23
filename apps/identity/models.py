from uuid import uuid4

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.identity.managers import UserManager


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
    objects = UserManager()

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
        return (
            self.is_active
            and self.status == self.AccountStatus.ACTIVE
            and self.is_email_verified
            and self.organization_id is not None
        )

    @property
    def can_govern_organization(self) -> bool:
        return self.can_operate and self.is_organization_titular

    def is_operational_member_of(self, organization) -> bool:
        organization_id = getattr(organization, "pk", organization)
        return self.can_operate and self.organization_id == organization_id

    def save(self, *args, **kwargs):
        """Keep Django's authentication flag aligned with terminal states.

        ``PENDING_APPROVAL`` remains authentication-capable so the requester can
        verify their email and see the public account-state messaging. Rejected
        and expired requests transition to ``INACTIVE`` and must invalidate any
        existing authenticated session on the next request.
        """
        if self.status == self.AccountStatus.INACTIVE:
            self.is_active = False
            self.is_organization_titular = False
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {
                    "is_active",
                    "is_organization_titular",
                }
        super().save(*args, **kwargs)

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
        self.requester.is_active = True
        self.requester.save(update_fields=["status", "is_active"])
        self.save(update_fields=["status", "decided_by", "decided_at"])

    def mark_rejected(self, *, actor: User) -> None:
        self.status = self.Status.REJECTED
        self.decided_by = actor
        self.decided_at = timezone.now()
        self.requester.status = User.AccountStatus.INACTIVE
        self.requester.is_active = False
        self.requester.is_organization_titular = False
        self.requester.save(
            update_fields=["status", "is_active", "is_organization_titular"]
        )
        self.save(update_fields=["status", "decided_by", "decided_at"])

    def mark_expired(self, *, occurred_at=None) -> None:
        self.status = self.Status.EXPIRED
        self.decided_by = None
        self.decided_at = occurred_at or timezone.now()
        self.requester.status = User.AccountStatus.INACTIVE
        self.requester.is_active = False
        self.requester.is_organization_titular = False
        self.requester.save(
            update_fields=["status", "is_active", "is_organization_titular"]
        )
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


class IdentityAuditEntry(models.Model):
    """Immutable projection of identity-governance domain events."""

    class EventType(models.TextChoices):
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

    event_type = models.CharField(
        _("Tipo de evento"),
        max_length=40,
        choices=EventType.choices,
    )
    organization = models.ForeignKey(
        "corporate.Organization",
        on_delete=models.PROTECT,
        related_name="identity_audit_entries",
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="identity_audit_actions",
        null=True,
        blank=True,
    )
    subject = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="identity_audit_subjects",
        null=True,
        blank=True,
    )
    secondary_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="secondary_identity_audit_entries",
        null=True,
        blank=True,
    )
    join_request = models.ForeignKey(
        OrganizationJoinRequest,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
        null=True,
        blank=True,
    )
    description = models.CharField(_("Descripción"), max_length=255)
    snapshot = models.JSONField(_("Snapshot"), default=dict, blank=True)
    occurred_at = models.DateTimeField(_("Fecha del evento"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Entrada de auditoría de identidad")
        verbose_name_plural = _("Entradas de auditoría de identidad")
        ordering = ["-occurred_at", "-id"]

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.organization}"
