from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    Custom user model for VIMER.
    Represents the human operator acting on behalf of an organization.
    """
    email = models.EmailField(_("email address"), unique=True)
    organization = models.ForeignKey(
        'corporate.Organization', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="members"
    )

    class Meta:
        verbose_name = _("usuario")
        verbose_name_plural = _("usuarios")

    def __str__(self):
        role_label = f" [{self.organization.role}]" if self.organization else ""
        return f"{self.username} ({self.email}){role_label}"
