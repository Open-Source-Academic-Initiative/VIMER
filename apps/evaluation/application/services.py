from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.evaluation.application.commands import (
    AssignChallengeEvaluationRolesCommand,
    AwardDecisionCommand,
    EvaluateApplicationCommand,
)
from apps.evaluation.application.exceptions import ChallengeEvaluationValidationError
from apps.evaluation.application.queries import (
    build_challenge_application_evaluation_summaries,
)
from apps.evaluation.domain.events import (
    ApplicationEvaluationRecorded,
    ChallengeAwarded,
    ChallengeEvaluationStarted,
)
from apps.evaluation.domain.signals import (
    publish_application_evaluation_recorded,
    publish_challenge_awarded,
    publish_challenge_evaluation_started,
)
from apps.evaluation.models import ApplicationCriterionEvaluation, AwardDecision
from apps.evaluation.models import ChallengeEvaluationRoleAssignment
from apps.marketplace.models import Application, Challenge


def _ensure_structured_criteria_items(challenge: Challenge) -> None:
    challenge.sync_evaluation_criteria_items()


def _challenge_has_required_evaluation_team(challenge: Challenge) -> bool:
    assignments = challenge.evaluation_role_assignments
    return (
        assignments.filter(role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR).exists()
        and assignments.filter(
            role=ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR
        ).exists()
    )


def _actor_has_evaluation_role(*, challenge: Challenge, actor, role: str) -> bool:
    return challenge.evaluation_role_assignments.filter(user=actor, role=role).exists()


@transaction.atomic
def assign_challenge_evaluation_roles(
    *,
    challenge: Challenge,
    actor,
    command: AssignChallengeEvaluationRolesCommand,
) -> Challenge:
    messages = []

    if actor.organization_id != challenge.publisher_id:
        messages.append(
            "Solo la organización publicadora puede definir el equipo de evaluación."
        )

    if challenge.status in {Challenge.Status.AWARDED, Challenge.Status.ARCHIVED}:
        messages.append(
            "No puedes redefinir el equipo de evaluación para un desafío adjudicado o archivado."
        )

    if not command.evaluator_user_ids:
        messages.append("Debes asignar al menos un evaluador designado.")

    if not command.adjudicator_user_id:
        messages.append("Debes asignar un adjudicador designado.")

    publisher_member_ids = set(
        challenge.publisher.members.values_list("pk", flat=True)
    )
    requested_user_ids = set(command.evaluator_user_ids) | set(command.observer_user_ids)
    requested_user_ids.add(command.adjudicator_user_id)

    if command.adjudicator_user_id and command.adjudicator_user_id not in publisher_member_ids:
        messages.append(
            "El adjudicador designado debe pertenecer a la organización publicadora."
        )

    invalid_user_ids = requested_user_ids - publisher_member_ids
    if invalid_user_ids:
        messages.append(
            "Todos los roles de evaluación deben asignarse a miembros de la organización publicadora."
        )

    if messages:
        raise ChallengeEvaluationValidationError(messages)

    ChallengeEvaluationRoleAssignment.objects.filter(challenge=challenge).delete()
    assignments = [
        ChallengeEvaluationRoleAssignment(
            challenge=challenge,
            user_id=user_id,
            role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR,
        )
        for user_id in command.evaluator_user_ids
    ]
    assignments.append(
        ChallengeEvaluationRoleAssignment(
            challenge=challenge,
            user_id=command.adjudicator_user_id,
            role=ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR,
        )
    )
    assignments.extend(
        ChallengeEvaluationRoleAssignment(
            challenge=challenge,
            user_id=user_id,
            role=ChallengeEvaluationRoleAssignment.Role.OBSERVER,
        )
        for user_id in command.observer_user_ids
    )
    for assignment in assignments:
        assignment.save()

    return challenge


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

    if not _challenge_has_required_evaluation_team(challenge):
        messages.append(
            "Debes definir al menos un evaluador designado y un adjudicador designado antes de iniciar la evaluación."
        )

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
    elif not _actor_has_evaluation_role(
        challenge=challenge,
        actor=actor,
        role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR,
    ):
        messages.append("Solo un evaluador designado puede evaluar propuestas.")

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

    application_summary = next(
        (
            evaluated_application.evaluation_summary
            for evaluated_application in build_challenge_application_evaluation_summaries(
                challenge
            )
            if evaluated_application.pk == application.pk
        ),
        None,
    )
    if application_summary is None:
        raise ChallengeEvaluationValidationError(
            ["No fue posible reconstruir el resumen de evaluación de la propuesta."]
        )

    publish_application_evaluation_recorded(
        ApplicationEvaluationRecorded(
            challenge_id=challenge.pk,
            application_id=application.pk,
            applicant_organization_id=application.applicant_id,
            publisher_organization_id=challenge.publisher_id,
            evaluated_by_user_id=actor.pk,
            evaluated_count=application_summary.evaluated_count,
            criteria_total=application_summary.criteria_total,
            total_score=application_summary.total_score,
            average_score=application_summary.average_score,
            ranking_position=application_summary.ranking_position,
            eligible_ranking_position=application_summary.eligible_ranking_position,
            occurred_at=timezone.now(),
        )
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
    elif not _actor_has_evaluation_role(
        challenge=challenge,
        actor=actor,
        role=ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR,
    ):
        messages.append("Solo el adjudicador designado puede adjudicar el desafío.")

    if challenge.status != Challenge.Status.UNDER_EVALUATION:
        messages.append("Solo los desafíos en evaluación pueden adjudicarse.")

    if AwardDecision.objects.filter(challenge=challenge).exists():
        messages.append("Este desafío ya tiene una decisión de adjudicación registrada.")

    winning_application = Application.objects.filter(
        pk=command.winning_application_id
    ).select_related("challenge", "applicant").first()
    winning_application_summary = None
    _ensure_structured_criteria_items(challenge)
    if winning_application is None:
        messages.append("Debes seleccionar una propuesta válida para adjudicar.")
    elif winning_application.challenge_id != challenge.pk:
        messages.append("La propuesta seleccionada no pertenece a este desafío.")
    elif not _application_has_complete_criterion_evaluations(winning_application):
        messages.append(
            "La propuesta ganadora debe tener todos sus criterios evaluados antes de adjudicar."
        )
    else:
        challenge_summaries = build_challenge_application_evaluation_summaries(challenge)
        winning_application_with_summary = next(
            (
                application
                for application in challenge_summaries
                if application.pk == winning_application.pk
            ),
            None,
        )
        if winning_application_with_summary is None:
            messages.append(
                "No fue posible reconstruir el resumen de evaluación de la propuesta seleccionada."
            )
        else:
            winning_application_summary = (
                winning_application_with_summary.evaluation_summary
            )

    if not (command.comment or "").strip():
        messages.append("Debes registrar un comentario de adjudicación.")

    if messages:
        raise ChallengeEvaluationValidationError(messages)

    decision = AwardDecision(
        challenge=challenge,
        winning_application=winning_application,
        comment=command.comment,
        winning_total_score=winning_application_summary.total_score,
        winning_average_score=winning_application_summary.average_score,
        winning_evaluated_criteria_count=winning_application_summary.evaluated_count,
        winning_criteria_total=winning_application_summary.criteria_total,
        winning_ranking_position=winning_application_summary.ranking_position,
        winning_eligible_ranking_position=(
            winning_application_summary.eligible_ranking_position
        ),
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
