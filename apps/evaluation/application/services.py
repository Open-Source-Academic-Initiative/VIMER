from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.evaluation.application.commands import AwardDecisionCommand
from apps.evaluation.application.exceptions import ChallengeEvaluationValidationError
from apps.evaluation.models import AwardDecision
from apps.marketplace.models import Application, Challenge


@transaction.atomic
def start_challenge_evaluation(*, challenge: Challenge, actor) -> Challenge:
    messages = []

    if actor.organization_id != challenge.publisher_id:
        messages.append("Solo la organización publicadora puede iniciar la evaluación.")

    if challenge.status != Challenge.Status.PUBLISHED:
        messages.append("Solo los desafíos publicados pueden pasar a evaluación.")

    if not challenge.applications.exists():
        messages.append("No puedes iniciar evaluación sin propuestas registradas.")

    if AwardDecision.objects.filter(challenge=challenge).exists():
        messages.append("Este desafío ya tiene una decisión de adjudicación registrada.")

    if messages:
        raise ChallengeEvaluationValidationError(messages)

    challenge.status = Challenge.Status.UNDER_EVALUATION
    challenge.save(update_fields=["status"])
    return challenge


@transaction.atomic
def adjudicate_challenge(
    *,
    challenge: Challenge,
    actor,
    command: AwardDecisionCommand,
) -> AwardDecision:
    messages = []

    if actor.organization_id != challenge.publisher_id:
        messages.append("Solo la organización publicadora puede adjudicar el desafío.")

    if challenge.status != Challenge.Status.UNDER_EVALUATION:
        messages.append("Solo los desafíos en evaluación pueden adjudicarse.")

    if AwardDecision.objects.filter(challenge=challenge).exists():
        messages.append("Este desafío ya tiene una decisión de adjudicación registrada.")

    winning_application = Application.objects.filter(
        pk=command.winning_application_id
    ).select_related("challenge", "applicant").first()
    if winning_application is None:
        messages.append("Debes seleccionar una propuesta válida para adjudicar.")
    elif winning_application.challenge_id != challenge.pk:
        messages.append("La propuesta seleccionada no pertenece a este desafío.")

    if not (command.comment or "").strip():
        messages.append("Debes registrar un comentario de adjudicación.")

    if messages:
        raise ChallengeEvaluationValidationError(messages)

    decision = AwardDecision(
        challenge=challenge,
        winning_application=winning_application,
        comment=command.comment,
        decided_by=actor,
    )

    try:
        decision.save()
        challenge.status = Challenge.Status.AWARDED
        challenge.save(update_fields=["status"])
    except IntegrityError as exc:
        raise ChallengeEvaluationValidationError(
            ["Este desafío ya tiene una decisión de adjudicación registrada."]
        ) from exc
    except ValidationError as exc:
        raise ChallengeEvaluationValidationError(exc.messages) from exc

    return decision
