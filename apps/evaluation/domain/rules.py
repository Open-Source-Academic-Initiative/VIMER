from apps.evaluation.domain.exceptions import EvaluationDomainRuleViolation
from apps.evaluation.domain.invariants import (
    INV_18_CHALLENGE_REQUIRES_EVALUATION_TEAM_BEFORE_EVALUATION,
    INV_19_EVALUATION_ROLES_ARE_LIMITED_TO_PUBLISHER_ORGANIZATION_MEMBERS,
    INV_20_ONLY_PUBLISHER_ORGANIZATION_CAN_GOVERN_EVALUATION,
    INV_21_ONLY_DESIGNATED_EVALUATORS_CAN_SCORE_PROPOSALS,
    INV_22_ONLY_DESIGNATED_ADJUDICATOR_CAN_ADJUDICATE,
    INV_28_AWARD_REQUIRES_CRITERION_COVERAGE,
    INV_31_AWARD_REQUIRES_COMPLETE_ACTIVE_PROPOSAL_COVERAGE,
)
from apps.evaluation.models import ChallengeEvaluationRoleAssignment
from apps.marketplace.models import Application, Challenge


def challenge_has_required_evaluation_team(challenge: Challenge) -> bool:
    assignments = challenge.evaluation_role_assignments
    return (
        assignments.filter(role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR).exists()
        and assignments.filter(
            role=ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR
        ).exists()
    )


def actor_has_evaluation_role(*, challenge: Challenge, actor, role: str) -> bool:
    return challenge.evaluation_role_assignments.filter(user=actor, role=role).exists()


def ensure_actor_belongs_to_publisher_organization(
    *,
    challenge: Challenge,
    actor,
    message: str,
) -> None:
    if actor.organization_id != challenge.publisher_id:
        raise EvaluationDomainRuleViolation(
            message,
            invariant_id=INV_20_ONLY_PUBLISHER_ORGANIZATION_CAN_GOVERN_EVALUATION,
        )


def ensure_requested_evaluation_role_members_belong_to_publisher_organization(
    *,
    challenge: Challenge,
    requested_user_ids: set[int],
) -> None:
    publisher_member_ids = set(challenge.publisher.members.values_list("pk", flat=True))
    invalid_user_ids = requested_user_ids - publisher_member_ids
    if invalid_user_ids:
        raise EvaluationDomainRuleViolation(
            "Todos los roles de evaluación deben asignarse a miembros de la organización publicadora.",
            invariant_id=INV_19_EVALUATION_ROLES_ARE_LIMITED_TO_PUBLISHER_ORGANIZATION_MEMBERS,
        )


def ensure_challenge_has_required_evaluation_team(challenge: Challenge) -> None:
    if not challenge_has_required_evaluation_team(challenge):
        raise EvaluationDomainRuleViolation(
            "Debes definir al menos un evaluador designado y un adjudicador designado antes de iniciar la evaluación.",
            invariant_id=INV_18_CHALLENGE_REQUIRES_EVALUATION_TEAM_BEFORE_EVALUATION,
        )


def ensure_actor_is_designated_evaluator(*, challenge: Challenge, actor) -> None:
    if not actor_has_evaluation_role(
        challenge=challenge,
        actor=actor,
        role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR,
    ):
        raise EvaluationDomainRuleViolation(
            "Solo un evaluador designado puede evaluar propuestas.",
            invariant_id=INV_21_ONLY_DESIGNATED_EVALUATORS_CAN_SCORE_PROPOSALS,
        )


def ensure_actor_is_designated_adjudicator(*, challenge: Challenge, actor) -> None:
    if not actor_has_evaluation_role(
        challenge=challenge,
        actor=actor,
        role=ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR,
    ):
        raise EvaluationDomainRuleViolation(
            "Solo el adjudicador designado puede adjudicar el desafío.",
            invariant_id=INV_22_ONLY_DESIGNATED_ADJUDICATOR_CAN_ADJUDICATE,
        )


def application_has_required_criterion_coverage_for_award(
    application: Application,
) -> bool:
    total_criteria = application.challenge.evaluation_criteria_items.count()
    if total_criteria == 0:
        return False

    covered_criteria = (
        application.criterion_evaluations.values("criterion_id").distinct().count()
    )
    return covered_criteria == total_criteria


def ensure_application_has_required_criterion_coverage_for_award(
    application: Application,
) -> None:
    if not application_has_required_criterion_coverage_for_award(application):
        raise EvaluationDomainRuleViolation(
            "La propuesta ganadora debe tener todos sus criterios evaluados antes de adjudicar.",
            invariant_id=INV_28_AWARD_REQUIRES_CRITERION_COVERAGE,
        )


def ensure_all_active_applications_have_complete_coverage(
    *,
    has_incomplete_active_applications: bool,
) -> None:
    if has_incomplete_active_applications:
        raise EvaluationDomainRuleViolation(
            "No puedes adjudicar el desafío mientras existan propuestas activas con criterios pendientes de evaluación.",
            invariant_id=INV_31_AWARD_REQUIRES_COMPLETE_ACTIVE_PROPOSAL_COVERAGE,
        )
