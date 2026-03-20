from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.evaluation.application.commands import (
    AwardDecisionCommand,
    EvaluateApplicationCommand,
)
from apps.evaluation.application.exceptions import ChallengeEvaluationValidationError
from apps.evaluation.domain.events import (
    ChallengeAwarded,
    ChallengeEvaluationStarted,
)
from apps.evaluation.domain.signals import (
    publish_challenge_awarded,
    publish_challenge_evaluation_started,
)
from apps.evaluation.models import ApplicationCriterionEvaluation, AwardDecision
from apps.marketplace.models import Application, Challenge


def _ensure_structured_criteria_items(challenge: Challenge) -> None:
    challenge.sync_evaluation_criteria_items()


def _application_has_complete_criterion_evaluations(application: Application) -> bool:
    total_criteria = application.challenge.evaluation_criteria_items.count()
    if total_criteria == 0:
        return False

    evaluated_criteria = application.criterion_evaluations.count()
    return evaluated_criteria == total_criteria


@transaction.atomic
def start_challenge_evaluation(*, challenge: Challenge, actor) -> Challenge:
    messages = []

    if actor.organization_id != challenge.publisher_id:
        messages.append("Solo la organización publicadora puede iniciar la evaluación.")

    if challenge.status != Challenge.Status.PUBLISHED:
        messages.append("Solo los desafíos publicados pueden pasar a evaluación.")

    if not challenge.applications.exists():
        messages.append("No puedes iniciar evaluación sin propuestas registradas.")

    if not challenge.has_evaluation_criteria():
        messages.append("No puedes iniciar evaluación sin criterios de evaluación definidos.")

    if AwardDecision.objects.filter(challenge=challenge).exists():
        messages.append("Este desafío ya tiene una decisión de adjudicación registrada.")

    if messages:
        raise ChallengeEvaluationValidationError(messages)

    _ensure_structured_criteria_items(challenge)
    challenge.status = Challenge.Status.UNDER_EVALUATION
    challenge.save(update_fields=["status"])
    publish_challenge_evaluation_started(
        ChallengeEvaluationStarted(
            challenge_id=challenge.pk,
            publisher_organization_id=challenge.publisher_id,
            started_by_user_id=actor.pk,
            occurred_at=timezone.now(),
        )
    )
    return challenge


@transaction.atomic
def evaluate_application_by_criteria(
    *,
    challenge: Challenge,
    application: Application,
    actor,
    command: EvaluateApplicationCommand,
) -> Application:
    messages = []

    if actor.organization_id != challenge.publisher_id:
        messages.append("Solo la organización publicadora puede evaluar propuestas.")

    if challenge.status != Challenge.Status.UNDER_EVALUATION:
        messages.append("Solo los desafíos en evaluación admiten evaluaciones por criterio.")

    if application.challenge_id != challenge.pk:
        messages.append("La propuesta evaluada no pertenece a este desafío.")

    _ensure_structured_criteria_items(challenge)
    criteria = list(challenge.evaluation_criteria_items.order_by("position"))
    if not criteria:
        messages.append("No hay criterios estructurados disponibles para evaluar este desafío.")

    expected_criterion_ids = {criterion.pk for criterion in criteria}
    received_criterion_ids = {assessment.criterion_id for assessment in command.assessments}

    if expected_criterion_ids and received_criterion_ids != expected_criterion_ids:
        messages.append("Debes evaluar todos los criterios definidos para la propuesta.")

    if messages:
        raise ChallengeEvaluationValidationError(messages)

    criterion_map = {criterion.pk: criterion for criterion in criteria}
    for assessment in command.assessments:
        if assessment.criterion_id not in criterion_map:
            raise ChallengeEvaluationValidationError(
                ["Uno de los criterios seleccionados no pertenece a este desafío."]
            )
        if not (assessment.comment or "").strip():
            raise ChallengeEvaluationValidationError(
                ["Debes registrar un comentario para cada criterio evaluado."]
            )

        ApplicationCriterionEvaluation.objects.update_or_create(
            application=application,
            criterion=criterion_map[assessment.criterion_id],
            defaults={
                "score": assessment.score,
                "comment": assessment.comment,
                "evaluated_by": actor,
            },
        )

    return application


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
    _ensure_structured_criteria_items(challenge)
    if winning_application is None:
        messages.append("Debes seleccionar una propuesta válida para adjudicar.")
    elif winning_application.challenge_id != challenge.pk:
        messages.append("La propuesta seleccionada no pertenece a este desafío.")
    elif not _application_has_complete_criterion_evaluations(winning_application):
        messages.append(
            "La propuesta ganadora debe tener todos sus criterios evaluados antes de adjudicar."
        )

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
        publish_challenge_awarded(
            ChallengeAwarded(
                challenge_id=challenge.pk,
                publisher_organization_id=challenge.publisher_id,
                winning_application_id=winning_application.pk,
                award_decision_id=decision.pk,
                decided_by_user_id=actor.pk,
                occurred_at=decision.decided_at,
            )
        )
    except IntegrityError as exc:
        raise ChallengeEvaluationValidationError(
            ["Este desafío ya tiene una decisión de adjudicación registrada."]
        ) from exc
    except ValidationError as exc:
        raise ChallengeEvaluationValidationError(exc.messages) from exc

    return decision
