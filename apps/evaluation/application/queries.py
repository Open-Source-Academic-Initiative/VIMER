from dataclasses import dataclass, replace
from datetime import datetime

from django.db.models import Prefetch

from apps.evaluation.domain.blind_references import (
    build_challenge_application_blind_reference_map,
)
from apps.evaluation.models import ApplicationCriterionEvaluation
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
