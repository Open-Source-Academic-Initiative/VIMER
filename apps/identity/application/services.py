from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.corporate.avatar_utils import generate_default_logo, validate_logo_image
from apps.corporate.models import Organization
from apps.identity.application.commands import RegisterOrganizationUserCommand
from apps.identity.application.exceptions import (
    DuplicateEmailError,
    DuplicateTaxIdError,
    DuplicateUsernameError,
    RegistrationValidationError,
)
from apps.identity.models import User


@transaction.atomic
def register_organization_user(command: RegisterOrganizationUserCommand) -> User:
    tax_id = command.tax_id.strip()
    username = User.normalize_username(command.username.strip())
    email = User.objects.normalize_email(command.email.strip().lower())
    first_name = command.first_name.strip()
    last_name = command.last_name.strip()
    business_name = command.business_name.strip()
    chamber_of_commerce_record = command.chamber_of_commerce_record.strip()
    contact_phone = command.contact_phone.strip()
    logo_upload = command.logo_upload

    if Organization.objects.filter(tax_id=tax_id).exists():
        raise DuplicateTaxIdError

    if User.objects.filter(username=username).exists():
        raise DuplicateUsernameError

    if User.objects.filter(email__iexact=email).exists():
        raise DuplicateEmailError

    organization = Organization(
        tax_id=tax_id,
        business_name=business_name,
        chamber_of_commerce_record=chamber_of_commerce_record,
        role=command.role,
        contact_email=email,
        contact_phone=contact_phone,
    )

    try:
        with transaction.atomic():
            if logo_upload:
                validate_logo_image(logo_upload)
                organization.logo = logo_upload
            else:
                organization.logo = generate_default_logo(
                    business_name=business_name,
                    tax_id=tax_id,
                )

            organization.full_clean()
            organization.save()

            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                organization=organization,
            )
            user.set_password(command.password)
            user.full_clean(validate_unique=False)
            user.save()
    except ValidationError as exc:
        raise RegistrationValidationError(
            messages=getattr(exc, "messages", None),
            message_dict=getattr(exc, "message_dict", None),
        ) from exc
    except IntegrityError as exc:
        if Organization.objects.filter(tax_id=tax_id).exists():
            raise DuplicateTaxIdError from exc
        if User.objects.filter(username=username).exists():
            raise DuplicateUsernameError from exc
        if User.objects.filter(email__iexact=email).exists():
            raise DuplicateEmailError from exc
        raise RegistrationValidationError(
            messages=["No fue posible completar el registro. Revisa la información e inténtalo nuevamente."],
        ) from exc

    return user
