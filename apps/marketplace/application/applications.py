from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import IntegrityError, transaction

from apps.corporate.models import Organization
from apps.marketplace.application.commands import (
    SaveApplicationDraftCommand,
    SubmitApplicationCommand,
)
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.domain.applications import (
    build_application_summary,
    ensure_challenge_is_open_for_applications,
    ensure_existing_application_is_not_submitted,
    ensure_organization_can_submit_application,
    get_existing_application_for_organization,
    ensure_submitted_application_is_complete,
)
from apps.marketplace.domain.exceptions import (
    ChallengeApplicationNotAllowed,
    ChallengeNotOpenForApplications,
    ExistingSubmittedApplication,
    IncompleteChallengeApplication,
)
from apps.marketplace.models import Application, ApplicationAttachment, Challenge


def _cleanup_uncommitted_files(created_attachments) -> None:
    for attachment in created_attachments:
        if attachment.file:
            attachment.file.storage.delete(attachment.file.name)


def _upsert_application(
    *,
    challenge: Challenge,
    applicant: Organization,
    status: str,
    problem_understanding: str,
    proposed_solution: str,
    capabilities_evidence: str,
    execution_plan: str,
    offered_amount=None,
    offer_currency: str = "",
    estimated_duration_days: int | None = None,
    attachments: tuple = (),
    uploaded_by=None,
) -> Application:
    challenge = Challenge.objects.select_for_update().get(pk=challenge.pk)
    existing_application = (
        Application.objects.select_for_update().filter(challenge=challenge, applicant=applicant).first()
    )
    ensure_challenge_is_open_for_applications(challenge)
    try:
        ensure_existing_application_is_not_submitted(existing_application)
    except ExistingSubmittedApplication as exc:
        raise DuplicateChallengeApplicationError from exc

    application = existing_application or Application(
        challenge=challenge,
        applicant=applicant,
    )
    application.status = status
    application.problem_understanding = problem_understanding
    application.proposed_solution = proposed_solution
    application.capabilities_evidence = capabilities_evidence
    application.execution_plan = execution_plan
    application.offered_amount = offered_amount
    application.offer_currency = offer_currency
    application.estimated_duration_days = estimated_duration_days
    if status == Application.Status.SUBMITTED:
        application.proposal_text = build_application_summary(
            problem_understanding=problem_understanding,
            proposed_solution=proposed_solution,
            capabilities_evidence=capabilities_evidence,
            execution_plan=execution_plan,
        )

    created_attachments = []
    try:
        application.save()
        if attachments:
            max_count = settings.MARKETPLACE_ATTACHMENT_MAX_COUNT
            existing_count = application.attachments.count()
            if existing_count + len(attachments) > max_count:
                raise ChallengeApplicationValidationError(
                    [
                        f"La propuesta no puede acumular más de {max_count} archivos "
                        f"adjuntos (ya tiene {existing_count})."
                    ]
                )
            for attachment in attachments:
                created_attachment = ApplicationAttachment.objects.create(
                    application=application,
                    file=attachment,
                    original_filename=attachment.name,
                    content_type=getattr(attachment, "content_type", ""),
                    size=attachment.size,
                    uploaded_by=uploaded_by,
                )
                created_attachments.append(created_attachment)
    except IntegrityError as exc:
        _cleanup_uncommitted_files(created_attachments)
        raise DuplicateChallengeApplicationError from exc
    except ValidationError as exc:
        _cleanup_uncommitted_files(created_attachments)
        raise ChallengeApplicationValidationError(exc.messages) from exc
    except ChallengeApplicationValidationError:
        _cleanup_uncommitted_files(created_attachments)
        raise

    return application


@transaction.atomic
def save_application_draft(
    challenge: Challenge,
    applicant: Organization,
    command: SaveApplicationDraftCommand,
    actor=None,
) -> Application:
    try:
        ensure_challenge_is_open_for_applications(challenge)
        ensure_organization_can_submit_application(applicant)
        ensure_existing_application_is_not_submitted(get_existing_application_for_organization(challenge, applicant))
    except ChallengeNotOpenForApplications as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc
    except ChallengeApplicationNotAllowed as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc
    except ExistingSubmittedApplication as exc:
        raise DuplicateChallengeApplicationError from exc

    return _upsert_application(
        challenge=challenge,
        applicant=applicant,
        status=Application.Status.DRAFT,
        problem_understanding=command.problem_understanding,
        proposed_solution=command.proposed_solution,
        capabilities_evidence=command.capabilities_evidence,
        execution_plan=command.execution_plan,
        offered_amount=command.offered_amount,
        offer_currency=command.offer_currency,
        estimated_duration_days=command.estimated_duration_days,
        attachments=command.attachments,
        uploaded_by=actor or applicant.members.order_by("pk").first(),
    )


@transaction.atomic
def submit_challenge_application(
    challenge: Challenge,
    applicant: Organization,
    command: SubmitApplicationCommand,
    actor=None,
) -> Application:
    try:
        ensure_challenge_is_open_for_applications(challenge)
        ensure_organization_can_submit_application(applicant)
        ensure_existing_application_is_not_submitted(get_existing_application_for_organization(challenge, applicant))
        ensure_submitted_application_is_complete(
            problem_understanding=command.problem_understanding,
            proposed_solution=command.proposed_solution,
            capabilities_evidence=command.capabilities_evidence,
            execution_plan=command.execution_plan,
        )
    except ExistingSubmittedApplication as exc:
        raise DuplicateChallengeApplicationError from exc
    except IncompleteChallengeApplication as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc
    except ChallengeNotOpenForApplications as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc
    except ChallengeApplicationNotAllowed as exc:
        raise ChallengeApplicationValidationError(exc.messages) from exc

    return _upsert_application(
        challenge=challenge,
        applicant=applicant,
        status=Application.Status.SUBMITTED,
        problem_understanding=command.problem_understanding,
        proposed_solution=command.proposed_solution,
        capabilities_evidence=command.capabilities_evidence,
        execution_plan=command.execution_plan,
        offered_amount=command.offered_amount,
        offer_currency=command.offer_currency,
        estimated_duration_days=command.estimated_duration_days,
        attachments=command.attachments,
        uploaded_by=actor or applicant.members.order_by("pk").first(),
    )


@transaction.atomic
def delete_application_draft_attachment(
    *,
    opaque_id: str,
    organization: Organization | None,
) -> ApplicationAttachment:
    """Remove an attachment from a draft owned by ``organization``.

    Submitted proposals are immutable, so attachments can only be deleted while
    the application is still a draft and the challenge remains open.
    """
    attachment = (
        ApplicationAttachment.objects.select_for_update()
        .select_related("application__challenge")
        .filter(opaque_id=opaque_id)
        .first()
    )
    if attachment is None or organization is None or attachment.application.applicant_id != organization.pk:
        raise ChallengeApplicationValidationError(["El adjunto no existe o no pertenece a tu organización."])

    application = attachment.application
    if application.status != Application.Status.DRAFT:
        raise ChallengeApplicationValidationError(["Los adjuntos de una propuesta enviada no pueden modificarse."])
    if not application.challenge.is_open_for_applications():
        raise ChallengeApplicationValidationError(["Este desafío no está abierto para guardar o enviar propuestas."])

    attachment.delete()
    return attachment
