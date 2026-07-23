from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class UserQuerySet(models.QuerySet):
    """Canonical queryset for representatives allowed to operate VIMER."""

    def operational(self):
        return self.filter(
            is_active=True,
            status="ACTIVE",
            is_email_verified=True,
            organization__isnull=False,
        )

    def operational_members_of(self, organization):
        organization_id = getattr(organization, "pk", organization)
        return self.operational().filter(organization_id=organization_id)


class UserManager(DjangoUserManager.from_queryset(UserQuerySet)):
    """Keep Django's user-creation API while exposing operational scopes."""
