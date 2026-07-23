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

from apps.corporate.avatar_utils import generate_default_logo, normalize_logo_image
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
from apps.identity.domain.events import (
    OrganizationOwnershipTransferred,
    RepresentativeJoinApproved,
    RepresentativeJoinExpired,
    RepresentativeJoinRejected,
    RepresentativeJoinRequested,
)
from apps.identity.domain.signals import (
    publish_organization_ownership_transferred,
    publish_representative_join_approved,
    publish_representative_join_expired,
    publish_representative_join_rejected,
    publish_representative_join_requested,
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


def _build_public_url(path: str) -> str:
    return f"{settings.PUBLIC_BASE_URL}{path}"


def _send_email_verification(user: User) -> None:
    token = EmailVerificationToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(days=2),
    )
    verification_url = _build_public_url(reverse("verify-email", args=[token.token]))
    try:
        send_mail(
            subject="Verifica tu correo en VIMER",
            message=(
                "Para activar tu correo en VIMER abre este enlace: "
                f"{verification_url}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except OSError as exc:
        # smtplib.SMTPException subclasses OSError; surface a friendly error and
        # let the surrounding transaction roll back so the user is never stranded
        # with an unverifiable account.
        raise RegistrationValidationError(
            messages=[
                "No fue posible enviar el correo de verificación. "
                "Inténtalo nuevamente en unos minutos."
            ]
        ) from exc


@transaction.atomic
def resend_email_verification(*, user: User) -> bool:
    """Replace outstanding tokens and send one fresh verification link.

    Returns ``False`` without revealing further state when the account is
    already verified. The user row lock serializes token replacement.
    """
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if locked_user.is_email_verified:
        return False

    EmailVerificationToken.objects.select_for_update().filter(
        user=locked_user,
        used_at__isnull=True,
    ).update(used_at=timezone.now())
    _send_email_verification(locked_user)
    return True


def _delete_rolled_back_organization_logo(organization) -> None:
    """Remove only a newly persisted blob whose database insert will roll back."""
    if organization is None:
        return
    logo = getattr(organization, "logo", None)
    if not logo or not logo.name or not getattr(logo, "_committed", False):
        return
    try:
        logo.delete(save=False)
    except OSError:
        # Preserve the original registration failure. Storage reconciliation can
        # detect an exceptional deletion failure without deleting unrelated files.
        pass


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
    new_organization = None

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
                new_organization = organization

                if logo_upload:
                    organization.logo = normalize_logo_image(
                        logo_upload,
                        filename_stem=business_name,
                    )
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
                join_request = OrganizationJoinRequest.objects.create(
                    organization=organization,
                    requester=user,
                    expires_at=timezone.now() + timedelta(days=14),
                )
                publish_representative_join_requested(
                    RepresentativeJoinRequested(
                        join_request_id=join_request.pk,
                        organization_id=organization.pk,
                        requester_user_id=user.pk,
                        occurred_at=timezone.now(),
                    )
                )
            _send_email_verification(user)
    except ValidationError as exc:
        _delete_rolled_back_organization_logo(new_organization)
        raise RegistrationValidationError(
            messages=getattr(exc, "messages", None),
            message_dict=getattr(exc, "message_dict", None),
        ) from exc
    except IntegrityError as exc:
        _delete_rolled_back_organization_logo(new_organization)
        if User.objects.filter(username=username).exists():
            raise DuplicateUsernameError from exc
        if User.objects.filter(email__iexact=email).exists():
            raise DuplicateEmailError from exc
        raise RegistrationValidationError(
            messages=["No fue posible completar el registro. Revisa la información e inténtalo nuevamente."],
        ) from exc
    except Exception:
        _delete_rolled_back_organization_logo(new_organization)
        raise

    return user


def _ensure_titular(actor: User) -> None:
    if not actor.can_govern_organization:
        raise OrganizationJoinRequestError(
            [
                "Solo un representante titular activo y con correo verificado "
                "puede ejecutar esta acción."
            ]
        )


def approve_organization_join_request(
    *,
    actor: User,
    command: DecideOrganizationJoinRequestCommand,
) -> OrganizationJoinRequest:
    expired = False
    with transaction.atomic():
        join_request = (
            OrganizationJoinRequest.objects.select_for_update()
            .select_related("organization")
            .get(pk=command.join_request_id)
        )
        locked_actor = User.objects.select_for_update().get(pk=actor.pk)
        requester = User.objects.select_for_update().get(
            pk=join_request.requester_id
        )
        join_request.requester = requester
        _ensure_titular(locked_actor)
        if join_request.organization_id != locked_actor.organization_id:
            raise OrganizationJoinRequestError(
                ["Solo puedes aprobar solicitudes de tu organización."]
            )
        if not join_request.is_pending:
            raise OrganizationJoinRequestError(["La solicitud ya no está pendiente."])

        occurred_at = timezone.now()
        if join_request.expires_at <= occurred_at:
            join_request.mark_expired(occurred_at=occurred_at)
            publish_representative_join_expired(
                RepresentativeJoinExpired(
                    join_request_id=join_request.pk,
                    organization_id=join_request.organization_id,
                    requester_user_id=requester.pk,
                    occurred_at=occurred_at,
                )
            )
            expired = True
        else:
            if requester.organization_id != join_request.organization_id:
                raise OrganizationJoinRequestError(
                    ["La solicitud no coincide con la organización del representante."]
                )
            join_request.mark_approved(actor=locked_actor)
            publish_representative_join_approved(
                RepresentativeJoinApproved(
                    join_request_id=join_request.pk,
                    organization_id=join_request.organization_id,
                    requester_user_id=requester.pk,
                    decided_by_user_id=locked_actor.pk,
                    occurred_at=join_request.decided_at,
                )
            )

    if expired:
        raise OrganizationJoinRequestError(
            ["La solicitud expiró y ya no puede ser aprobada."]
        )
    return join_request


def reject_organization_join_request(
    *,
    actor: User,
    command: DecideOrganizationJoinRequestCommand,
) -> OrganizationJoinRequest:
    expired = False
    with transaction.atomic():
        join_request = (
            OrganizationJoinRequest.objects.select_for_update()
            .select_related("organization")
            .get(pk=command.join_request_id)
        )
        locked_actor = User.objects.select_for_update().get(pk=actor.pk)
        requester = User.objects.select_for_update().get(
            pk=join_request.requester_id
        )
        join_request.requester = requester
        _ensure_titular(locked_actor)
        if join_request.organization_id != locked_actor.organization_id:
            raise OrganizationJoinRequestError(
                ["Solo puedes rechazar solicitudes de tu organización."]
            )
        if not join_request.is_pending:
            raise OrganizationJoinRequestError(["La solicitud ya no está pendiente."])

        occurred_at = timezone.now()
        if join_request.expires_at <= occurred_at:
            join_request.mark_expired(occurred_at=occurred_at)
            publish_representative_join_expired(
                RepresentativeJoinExpired(
                    join_request_id=join_request.pk,
                    organization_id=join_request.organization_id,
                    requester_user_id=requester.pk,
                    occurred_at=occurred_at,
                )
            )
            expired = True
        else:
            join_request.mark_rejected(actor=locked_actor)
            publish_representative_join_rejected(
                RepresentativeJoinRejected(
                    join_request_id=join_request.pk,
                    organization_id=join_request.organization_id,
                    requester_user_id=requester.pk,
                    decided_by_user_id=locked_actor.pk,
                    occurred_at=join_request.decided_at,
                )
            )

    if expired:
        raise OrganizationJoinRequestError(
            ["La solicitud expiró y ya no puede ser rechazada."]
        )
    return join_request


def transfer_organization_titularity(
    *,
    actor: User,
    command: TransferOrganizationTitularityCommand,
) -> User:
    if actor.pk is None or command.target_user_id == actor.pk:
        raise OrganizationTitularityTransferError(
            ["Selecciona otro representante operativo de la organización."]
        )

    with transaction.atomic():
        locked_users = {
            user.pk: user
            for user in User.objects.select_for_update()
            .filter(pk__in=sorted({actor.pk, command.target_user_id}))
            .order_by("pk")
        }
        locked_actor = locked_users.get(actor.pk)
        target = locked_users.get(command.target_user_id)
        if locked_actor is None or not locked_actor.can_govern_organization:
            raise OrganizationTitularityTransferError(
                [
                    "Solo un representante titular operativo puede transferir "
                    "la titularidad."
                ]
            )
        if (
            target is None
            or not target.is_operational_member_of(locked_actor.organization_id)
        ):
            raise OrganizationTitularityTransferError(
                [
                    "La titularidad solo puede transferirse a un representante "
                    "operativo de la misma organización."
                ]
            )

        locked_actor.is_organization_titular = False
        locked_actor.save(update_fields=["is_organization_titular"])
        target.is_organization_titular = True
        target.save(update_fields=["is_organization_titular"])
        publish_organization_ownership_transferred(
            OrganizationOwnershipTransferred(
                organization_id=locked_actor.organization_id,
                previous_titular_user_id=locked_actor.pk,
                new_titular_user_id=target.pk,
                transferred_by_user_id=locked_actor.pk,
                occurred_at=timezone.now(),
            )
        )
    return target


def expire_pending_organization_join_requests(*, now=None) -> int:
    """Expire due requests safely against concurrent approval/rejection."""
    occurred_at = now or timezone.now()
    due_request_ids = list(
        OrganizationJoinRequest.objects.filter(
            status=OrganizationJoinRequest.Status.PENDING,
            expires_at__lte=occurred_at,
        )
        .order_by("pk")
        .values_list("pk", flat=True)
    )
    expired_count = 0
    for join_request_id in due_request_ids:
        with transaction.atomic():
            join_request = (
                OrganizationJoinRequest.objects.select_for_update()
                .filter(
                    pk=join_request_id,
                    status=OrganizationJoinRequest.Status.PENDING,
                    expires_at__lte=occurred_at,
                )
                .first()
            )
            if join_request is None:
                continue
            requester = User.objects.select_for_update().get(
                pk=join_request.requester_id
            )
            join_request.requester = requester
            join_request.mark_expired(occurred_at=occurred_at)
            publish_representative_join_expired(
                RepresentativeJoinExpired(
                    join_request_id=join_request.pk,
                    organization_id=join_request.organization_id,
                    requester_user_id=requester.pk,
                    occurred_at=occurred_at,
                )
            )
            expired_count += 1
    return expired_count
