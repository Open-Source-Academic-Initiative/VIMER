from dataclasses import dataclass, replace
from datetime import datetime
from fractions import Fraction
from itertools import groupby

from django.db.models import Prefetch

from apps.evaluation.domain.blind_references import (
    build_challenge_application_blind_reference_map,
)
from apps.evaluation.models import (
    ApplicationCriterionEvaluation,
    AwardDecision,
    ChallengeEvaluationRoleAssignment,
    ChallengeTimelineEntry,
)
from apps.marketplace.models import Application, Challenge


@dataclass(frozen=True)
class CriterionAssessmentDetail:
    score: int
    comment: str
    evaluated_by_username: str
    evaluated_at: datetime


@dataclass(frozen=True)
class CriterionEvaluationSummary:
    label: str
    evaluation_count: int
    average_score: float | None
    evaluations: tuple[CriterionAssessmentDetail, ...]


@dataclass(frozen=True)
class ApplicationEvaluationSummary:
    blind_reference: str
    evaluated_count: int
    criteria_total: int
    missing_criteria_count: int
    missing_criteria_labels: tuple[str, ...]
    is_complete: bool
    assessment_count: int
    total_score: int
    average_score: float | None
    ranking_position: int | None
    eligible_ranking_position: int | None
    is_tied: bool
    tied_application_count: int
    criterion_results: tuple[CriterionEvaluationSummary, ...]


@dataclass(frozen=True)
class EvaluationTeamSnapshot:
    evaluators: tuple[ChallengeEvaluationRoleAssignment, ...]
    adjudicator: ChallengeEvaluationRoleAssignment | None
    observers: tuple[ChallengeEvaluationRoleAssignment, ...]


@dataclass(frozen=True)
class ChallengePublisherDetailReadModel:
    award_decision: AwardDecision | None
    timeline_entries: tuple[ChallengeTimelineEntry, ...]
    evaluation_role_assignments: tuple[ChallengeEvaluationRoleAssignment, ...]
    evaluation_team: EvaluationTeamSnapshot
    challenge_applications: tuple[Application, ...]
    can_manage_evaluation_team: bool
    show_applicant_identity: bool
    has_required_evaluation_team: bool
    can_evaluate_applications: bool
    can_adjudicate_challenge: bool
    can_start_evaluation: bool
    can_award_challenge: bool
    pending_award_applications: tuple[Application, ...]
    best_available_applications: tuple[Application, ...]
    award_blocking_messages: tuple[str, ...]


AWARD_BLOCKED_MESSAGE = (
    "No puedes adjudicar el desafío mientras existan propuestas activas con criterios "
    "pendientes de evaluación."
)


def build_pending_award_messages(applications: list[Application] | tuple[Application, ...]) -> tuple[str, ...]:
    pending_applications = [
        application
        for application in applications
        if not application.evaluation_summary.is_complete
    ]
    if not pending_applications:
        return ()

    pending_labels = ", ".join(
        (
            f"{application.evaluation_summary.blind_reference} "
            f"({application.evaluation_summary.missing_criteria_count} "
            f"criterio{'s' if application.evaluation_summary.missing_criteria_count != 1 else ''} pendiente"
            f"{'s' if application.evaluation_summary.missing_criteria_count != 1 else ''})"
        )
        for application in pending_applications
    )
    return (
        AWARD_BLOCKED_MESSAGE,
        f"Pendientes: {pending_labels}.",
    )


def build_application_ranking_snapshot(application: Application) -> dict:
    summary = application.evaluation_summary
    return {
        "application_id": application.pk,
        "blind_reference": summary.blind_reference,
        "ranking_position": summary.ranking_position,
        "eligible_ranking_position": summary.eligible_ranking_position,
        "average_score": summary.average_score,
        "assessment_count": summary.assessment_count,
        "evaluated_count": summary.evaluated_count,
        "criteria_total": summary.criteria_total,
    }


def build_challenge_application_evaluation_summaries(
    challenge: Challenge,
    *,
    reveal_applicant_identity: bool = False,
) -> list[Application]:
    challenge.sync_evaluation_criteria_items()
    criteria = list(challenge.evaluation_criteria_items.order_by("position"))
    criteria_total = len(criteria)
    blind_reference_map = build_challenge_application_blind_reference_map(challenge)
    queryset = challenge.applications.submitted().prefetch_related(
        Prefetch(
            "criterion_evaluations",
            queryset=ApplicationCriterionEvaluation.objects.select_related(
                "criterion",
                "evaluated_by",
            ).order_by("criterion__position", "evaluated_by__username", "id"),
        )
    )
    if reveal_applicant_identity:
        queryset = queryset.select_related("applicant")
    applications = list(queryset)

    complete_application_scores: list[tuple[Application, Fraction]] = []

    for application in applications:
        evaluations_by_criterion = {}
        all_evaluations = list(application.criterion_evaluations.all())
        for evaluation in all_evaluations:
            evaluations_by_criterion.setdefault(evaluation.criterion_id, []).append(
                evaluation
            )

        evaluated_count = len(evaluations_by_criterion)
        assessment_count = len(all_evaluations)
        total_score = sum(evaluation.score for evaluation in all_evaluations)
        criterion_score_components: list[Fraction] = []
        missing_criteria_labels: list[str] = []
        criterion_results = []

        for criterion in criteria:
            criterion_evaluations = tuple(
                evaluations_by_criterion.get(criterion.pk, ())
            )
            criterion_average = None
            if criterion_evaluations:
                criterion_average_fraction = Fraction(
                    sum(evaluation.score for evaluation in criterion_evaluations),
                    len(criterion_evaluations),
                )
                criterion_score_components.append(criterion_average_fraction)
                criterion_average = float(criterion_average_fraction)
            else:
                missing_criteria_labels.append(criterion.label)

            criterion_results.append(
                CriterionEvaluationSummary(
                    label=criterion.label,
                    evaluation_count=len(criterion_evaluations),
                    average_score=criterion_average,
                    evaluations=tuple(
                        CriterionAssessmentDetail(
                            score=evaluation.score,
                            comment=evaluation.comment,
                            evaluated_by_username=evaluation.evaluated_by.username,
                            evaluated_at=evaluation.evaluated_at,
                        )
                        for evaluation in criterion_evaluations
                    ),
                )
            )

        average_score = None
        average_score_fraction = None
        if criterion_score_components:
            average_score_fraction = sum(
                criterion_score_components,
                start=Fraction(0, 1),
            ) / len(criterion_score_components)
            average_score = float(average_score_fraction)

        is_complete = criteria_total > 0 and evaluated_count == criteria_total

        application.evaluation_summary = ApplicationEvaluationSummary(
            blind_reference=blind_reference_map[application.pk],
            evaluated_count=evaluated_count,
            criteria_total=criteria_total,
            missing_criteria_count=len(missing_criteria_labels),
            missing_criteria_labels=tuple(missing_criteria_labels),
            is_complete=is_complete,
            assessment_count=assessment_count,
            total_score=total_score,
            average_score=average_score,
            ranking_position=None,
            eligible_ranking_position=None,
            is_tied=False,
            tied_application_count=1,
            criterion_results=tuple(criterion_results),
        )
        application.blind_reference = blind_reference_map[application.pk]
        if is_complete and average_score_fraction is not None:
            complete_application_scores.append((application, average_score_fraction))

    complete_application_scores.sort(
        key=lambda item: (
            -item[1],
            item[0].pk,
        )
    )
    complete_applications = [application for application, _ in complete_application_scores]
    incomplete_applications = [
        application
        for application in applications
        if not application.evaluation_summary.is_complete
    ]
    incomplete_applications.sort(
        key=lambda application: (
            -application.evaluation_summary.evaluated_count,
            -(
                application.evaluation_summary.average_score
                if application.evaluation_summary.average_score is not None
                else -1
            ),
            application.pk,
        )
    )

    visible_position = 0
    for _, grouped_applications_iter in groupby(
        complete_application_scores,
        key=lambda item: item[1],
    ):
        grouped_applications = [application for application, _ in grouped_applications_iter]
        visible_position += 1
        tie_count = len(grouped_applications)
        for application in grouped_applications:
            summary = application.evaluation_summary
            application.evaluation_summary = replace(
                summary,
                ranking_position=visible_position,
                eligible_ranking_position=visible_position,
                is_tied=tie_count > 1,
                tied_application_count=tie_count,
            )

    return complete_applications + incomplete_applications


def build_challenge_publisher_detail_read_model(
    *,
    challenge: Challenge,
    requester,
) -> ChallengePublisherDetailReadModel:
    requester_org_id = getattr(requester, "organization_id", None)
    can_manage_evaluation_team = requester_org_id == challenge.publisher_id

    if not can_manage_evaluation_team:
        return ChallengePublisherDetailReadModel(
            award_decision=None,
            timeline_entries=(),
            evaluation_role_assignments=(),
            evaluation_team=EvaluationTeamSnapshot(
                evaluators=(),
                adjudicator=None,
                observers=(),
            ),
            challenge_applications=(),
            can_manage_evaluation_team=False,
            show_applicant_identity=False,
            has_required_evaluation_team=False,
            can_evaluate_applications=False,
            can_adjudicate_challenge=False,
            can_start_evaluation=False,
            can_award_challenge=False,
            pending_award_applications=(),
            best_available_applications=(),
            award_blocking_messages=(),
        )

    award_decision = AwardDecision.objects.filter(
        challenge=challenge
    ).select_related(
        "winning_application__applicant",
        "decided_by",
    ).first()
    timeline_entries = tuple(
        ChallengeTimelineEntry.objects.filter(
            challenge=challenge
        ).select_related(
            "actor",
            "award_decision__winning_application__applicant",
        )
    )
    evaluation_role_assignments = tuple(
        challenge.evaluation_role_assignments.select_related("user")
    )
    evaluators = tuple(
        assignment
        for assignment in evaluation_role_assignments
        if assignment.role == ChallengeEvaluationRoleAssignment.Role.EVALUATOR
    )
    adjudicator = next(
        (
            assignment
            for assignment in evaluation_role_assignments
            if assignment.role == ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR
        ),
        None,
    )
    observers = tuple(
        assignment
        for assignment in evaluation_role_assignments
        if assignment.role == ChallengeEvaluationRoleAssignment.Role.OBSERVER
    )
    show_applicant_identity = award_decision is not None
    challenge_applications = tuple(
        build_challenge_application_evaluation_summaries(
            challenge,
            reveal_applicant_identity=show_applicant_identity,
        )
    )
    pending_award_applications = tuple(
        application
        for application in challenge_applications
        if not application.evaluation_summary.is_complete
    )
    best_available_applications = tuple(
        application
        for application in challenge_applications
        if application.evaluation_summary.ranking_position == 1
    )
    award_blocking_messages = build_pending_award_messages(challenge_applications)
    has_required_evaluation_team = bool(evaluators) and adjudicator is not None
    can_evaluate_applications = any(
        assignment.user_id == requester.pk
        and assignment.role == ChallengeEvaluationRoleAssignment.Role.EVALUATOR
        for assignment in evaluation_role_assignments
    )
    can_adjudicate_challenge = any(
        assignment.user_id == requester.pk
        and assignment.role == ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR
        for assignment in evaluation_role_assignments
    )

    return ChallengePublisherDetailReadModel(
        award_decision=award_decision,
        timeline_entries=timeline_entries,
        evaluation_role_assignments=evaluation_role_assignments,
        evaluation_team=EvaluationTeamSnapshot(
            evaluators=evaluators,
            adjudicator=adjudicator,
            observers=observers,
        ),
        challenge_applications=challenge_applications,
        can_manage_evaluation_team=True,
        show_applicant_identity=show_applicant_identity,
        has_required_evaluation_team=has_required_evaluation_team,
        can_evaluate_applications=can_evaluate_applications,
        can_adjudicate_challenge=can_adjudicate_challenge,
        can_start_evaluation=(
            challenge.status == Challenge.Status.PUBLISHED
            and challenge.applications.submitted().exists()
            and has_required_evaluation_team
            and award_decision is None
        ),
        can_award_challenge=(
            can_adjudicate_challenge
            and challenge.status == Challenge.Status.UNDER_EVALUATION
            and challenge.applications.submitted().exists()
            and award_decision is None
            and not pending_award_applications
            and bool(best_available_applications)
        ),
        pending_award_applications=pending_award_applications,
        best_available_applications=best_available_applications,
        award_blocking_messages=award_blocking_messages,
    )
