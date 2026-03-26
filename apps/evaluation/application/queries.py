from dataclasses import dataclass, replace
from datetime import datetime

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
    is_complete: bool
    assessment_count: int
    total_score: int
    average_score: float | None
    ranking_position: int | None
    eligible_ranking_position: int | None
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


def build_challenge_application_evaluation_summaries(
    challenge: Challenge,
    *,
    reveal_applicant_identity: bool = False,
) -> list[Application]:
    challenge.sync_evaluation_criteria_items()
    criteria = list(challenge.evaluation_criteria_items.order_by("position"))
    criteria_total = len(criteria)
    blind_reference_map = build_challenge_application_blind_reference_map(challenge)
    queryset = challenge.applications.prefetch_related(
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
        average_score = None
        if assessment_count:
            average_score = total_score / assessment_count

        application.evaluation_summary = ApplicationEvaluationSummary(
            blind_reference=blind_reference_map[application.pk],
            evaluated_count=evaluated_count,
            criteria_total=criteria_total,
            is_complete=(
                criteria_total > 0 and evaluated_count == criteria_total
            ),
            assessment_count=assessment_count,
            total_score=total_score,
            average_score=average_score,
            ranking_position=None,
            eligible_ranking_position=None,
            criterion_results=tuple(
                CriterionEvaluationSummary(
                    label=criterion.label,
                    evaluation_count=len(evaluations_by_criterion.get(criterion.pk, ())),
                    average_score=(
                        sum(
                            evaluation.score
                            for evaluation in evaluations_by_criterion.get(
                                criterion.pk,
                                (),
                            )
                        )
                        / len(evaluations_by_criterion[criterion.pk])
                        if criterion.pk in evaluations_by_criterion
                        else None
                    ),
                    evaluations=tuple(
                        CriterionAssessmentDetail(
                            score=evaluation.score,
                            comment=evaluation.comment,
                            evaluated_by_username=evaluation.evaluated_by.username,
                            evaluated_at=evaluation.evaluated_at,
                        )
                        for evaluation in evaluations_by_criterion.get(criterion.pk, ())
                    ),
                )
                for criterion in criteria
            ),
        )
        application.blind_reference = blind_reference_map[application.pk]

    applications.sort(
        key=lambda application: (
            0 if application.evaluation_summary.is_complete else 1,
            -(
                application.evaluation_summary.average_score
                if application.evaluation_summary.average_score is not None
                else -1
            ),
            -application.evaluation_summary.total_score,
            -application.evaluation_summary.assessment_count,
            application.pk,
        )
    )

    eligible_ranking_position = 0
    for ranking_position, application in enumerate(applications, start=1):
        summary = application.evaluation_summary
        current_eligible_position = None
        if summary.is_complete:
            eligible_ranking_position += 1
            current_eligible_position = eligible_ranking_position

        application.evaluation_summary = replace(
            summary,
            ranking_position=ranking_position,
            eligible_ranking_position=current_eligible_position,
        )

    return applications


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
            and challenge.applications.exists()
            and has_required_evaluation_team
            and award_decision is None
        ),
        can_award_challenge=(
            can_adjudicate_challenge
            and challenge.status == Challenge.Status.UNDER_EVALUATION
            and challenge.applications.exists()
            and award_decision is None
        ),
    )
