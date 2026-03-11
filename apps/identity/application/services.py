from django.db import IntegrityError, transaction

from apps.corporate.models import Organization
from apps.identity.application.commands import RegisterOrganizationUserCommand
from apps.identity.application.exceptions import DuplicateTaxIdError
from apps.identity.models import User


@transaction.atomic
def register_organization_user(command: RegisterOrganizationUserCommand) -> User:
    try:
        organization = Organization.objects.create(
            tax_id=command.tax_id,
            business_name=command.business_name,
            chamber_of_commerce_record=command.chamber_of_commerce_record,
            role=command.role,
            contact_email=command.email,
            contact_phone=command.contact_phone,
        )
    except IntegrityError as exc:
        raise DuplicateTaxIdError from exc

    user = User.objects.create_user(
        username=command.username,
        email=command.email,
        password=command.password,
        first_name=command.first_name,
        last_name=command.last_name,
        organization=organization,
    )
    return user
