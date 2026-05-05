import json
from datetime import timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from apps.corporate.avatar_utils import generate_default_logo, validate_logo_image
from apps.corporate.models import Organization
from apps.identity.application.commands import (
    DecideOrganizationJoinRequestCommand,
    RegisterOrganizationUserCommand,
    TransferOrganizationTitularityCommand,
)
from apps.identity.application.exceptions import (
    DuplicateEmailError,
    DuplicateUsernameError,
    OrganizationJoinRequestError,
    OrganizationTitularityTransferError,
    RegistrationValidationError,
)
from apps.identity.models import EmailVerificationToken, OrganizationJoinRequest, User


def _verify_turnstile_token(token: str) -> None:
    if not settings.TURNSTILE_SECRET_KEY:
        return

    data = urlencode(
        {
            "secret": settings.TURNSTILE_SECRET_KEY,
            "response": token,
        }
    ).encode()
    request = Request(settings.TURNSTILE_VERIFY_URL, data=data, method="POST")
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode())
    except OSError as exc:
        raise RegistrationValidationError(
            messages=["No fue posible validar la verificación anti-spam."]
        ) from exc

    if not payload.get("success"):
        raise RegistrationValidationError(
            messages=["La verificación anti-spam no fue aprobada."]
        )


def _send_email_verification(user: User) -> None:
    token = EmailVerificationToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(days=2),
    )
    verification_path = reverse("verify-email", args=[token.token])
    send_mail(
        subject="Verifica tu correo en VIMER",
        message=(
            "Para activar tu correo en VIMER abre este enlace: "
            f"{verification_path}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


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

    if not command.accepted_terms or not command.accepted_privacy_policy:
        raise RegistrationValidationError(
            messages=[
                "Debes aceptar los Términos y Condiciones y la Política de Tratamiento de Datos."
            ]
        )

    _verify_turnstile_token(command.turnstile_token)

    if User.objects.filter(username=username).exists():
        raise DuplicateUsernameError

    if User.objects.filter(email__iexact=email).exists():
        raise DuplicateEmailError

    existing_organization = Organization.objects.filter(tax_id=tax_id).first()

    try:
        with transaction.atomic():
            if existing_organization is None:
                organization = Organization(
                    tax_id=tax_id,
                    business_name=business_name,
                    chamber_of_commerce_record=chamber_of_commerce_record,
                    role=command.role,
                    contact_email=email,
                    contact_phone=contact_phone,
                )

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
                account_status = User.AccountStatus.ACTIVE
                is_titular = True
            else:
                organization = existing_organization
                account_status = User.AccountStatus.PENDING_APPROVAL
                is_titular = False

            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                organization=organization,
                status=account_status,
                is_organization_titular=is_titular,
                accepted_terms_version=settings.LEGAL_TERMS_VERSION,
                accepted_privacy_policy_version=settings.LEGAL_PRIVACY_VERSION,
            )
            user.set_password(command.password)
            user.full_clean(validate_unique=False)
            user.save()

            if existing_organization is not None:
                OrganizationJoinRequest.objects.create(
                    organization=organization,
                    requester=user,
                    expires_at=timezone.now() + timedelta(days=14),
                )
            _send_email_verification(user)
    except ValidationError as exc:
        raise RegistrationValidationError(
            messages=getattr(exc, "messages", None),
            message_dict=getattr(exc, "message_dict", None),
        ) from exc
    except IntegrityError as exc:
        if User.objects.filter(username=username).exists():
            raise DuplicateUsernameError from exc
        if User.objects.filter(email__iexact=email).exists():
            raise DuplicateEmailError from exc
        raise RegistrationValidationError(
            messages=["No fue posible completar el registro. Revisa la información e inténtalo nuevamente."],
        ) from exc

    return user


def _ensure_titular(actor: User) -> None:
    if not actor.is_organization_titular or actor.status != User.AccountStatus.ACTIVE:
        raise OrganizationJoinRequestError(
            ["Solo el representante titular puede ejecutar esta acción."]
        )


@transaction.atomic
def approve_organization_join_request(
    *,
    actor: User,
    command: DecideOrganizationJoinRequestCommand,
) -> OrganizationJoinRequest:
    _ensure_titular(actor)
    join_request = OrganizationJoinRequest.objects.select_for_update().select_related(
        "organization",
        "requester",
    ).get(pk=command.join_request_id)
    if join_request.organization_id != actor.organization_id:
        raise OrganizationJoinRequestError(
            ["Solo puedes aprobar solicitudes de tu organización."]
        )
    if not join_request.is_pending:
        raise OrganizationJoinRequestError(["La solicitud ya no está pendiente."])
    join_request.mark_approved(actor=actor)
    return join_request


@transaction.atomic
def reject_organization_join_request(
    *,
    actor: User,
    command: DecideOrganizationJoinRequestCommand,
) -> OrganizationJoinRequest:
    _ensure_titular(actor)
    join_request = OrganizationJoinRequest.objects.select_for_update().select_related(
        "organization",
        "requester",
    ).get(pk=command.join_request_id)
    if join_request.organization_id != actor.organization_id:
        raise OrganizationJoinRequestError(
            ["Solo puedes rechazar solicitudes de tu organización."]
        )
    if not join_request.is_pending:
        raise OrganizationJoinRequestError(["La solicitud ya no está pendiente."])
    join_request.mark_rejected(actor=actor)
    return join_request


@transaction.atomic
def transfer_organization_titularity(
    *,
    actor: User,
    command: TransferOrganizationTitularityCommand,
) -> User:
    if not actor.is_organization_titular or actor.status != User.AccountStatus.ACTIVE:
        raise OrganizationTitularityTransferError(
            ["Solo el representante titular puede transferir la titularidad."]
        )
    target = User.objects.select_for_update().filter(
        pk=command.target_user_id,
        organization_id=actor.organization_id,
        status=User.AccountStatus.ACTIVE,
    ).first()
    if target is None:
        raise OrganizationTitularityTransferError(
            ["La titularidad solo puede transferirse a un representante activo de la misma organización."]
        )
    actor.is_organization_titular = False
    actor.save(update_fields=["is_organization_titular"])
    target.is_organization_titular = True
    target.save(update_fields=["is_organization_titular"])
    return target
