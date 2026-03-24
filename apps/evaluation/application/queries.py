from dataclasses import dataclass, replace

from django.db.models import Count, Prefetch

from apps.evaluation.models import ApplicationCriterionEvaluation
from apps.marketplace.models import Application, Challenge


@dataclass(frozen=True)
class CriterionEvaluationSummary:
    label: str
    score: int | None
    comment: str
    evaluated_by_username: str | None


@dataclass(frozen=True)
class ApplicationEvaluationSummary:
    evaluated_count: int
    criteria_total: int
    is_complete: bool
    total_score: int
    average_score: float | None
    ranking_position: int | None
    eligible_ranking_position: int | None
    criterion_results: tuple[CriterionEvaluationSummary, ...]


def build_challenge_application_evaluation_summaries(challenge: Challenge) -> list[Application]:
    challenge.sync_evaluation_criteria_items()
    criteria = list(challenge.evaluation_criteria_items.order_by("position"))
    criteria_total = len(criteria)
    applications = list(
        challenge.applications.select_related("applicant").prefetch_related(
            Prefetch(
                "criterion_evaluations",
                queryset=ApplicationCriterionEvaluation.objects.select_related(
                    "criterion",
                    "evaluated_by",
                ).order_by("criterion__position", "id"),
            )
        ).annotate(
            evaluated_count=Count("criterion_evaluations", distinct=True),
        )
    )

    for application in applications:
        evaluations_by_criterion = {
            evaluation.criterion_id: evaluation
            for evaluation in application.criterion_evaluations.all()
        }
        total_score = sum(
            evaluation.score for evaluation in evaluations_by_criterion.values()
        )
        average_score = None
        if application.evaluated_count:
            average_score = total_score / application.evaluated_count

        application.evaluation_summary = ApplicationEvaluationSummary(
            evaluated_count=application.evaluated_count,
            criteria_total=criteria_total,
            is_complete=(
                criteria_total > 0 and application.evaluated_count == criteria_total
            ),
            total_score=total_score,
            average_score=average_score,
            ranking_position=None,
            eligible_ranking_position=None,
            criterion_results=tuple(
                CriterionEvaluationSummary(
                    label=criterion.label,
                    score=(
                        evaluations_by_criterion[criterion.pk].score
                        if criterion.pk in evaluations_by_criterion
                        else None
                    ),
                    comment=(
                        evaluations_by_criterion[criterion.pk].comment
                        if criterion.pk in evaluations_by_criterion
                        else ""
                    ),
                    evaluated_by_username=(
                        evaluations_by_criterion[criterion.pk].evaluated_by.username
                        if criterion.pk in evaluations_by_criterion
                        else None
                    ),
                )
                for criterion in criteria
            ),
        )

    applications.sort(
        key=lambda application: (
            0 if application.evaluation_summary.is_complete else 1,
            -(
                application.evaluation_summary.average_score
                if application.evaluation_summary.average_score is not None
                else -1
            ),
            -application.evaluation_summary.total_score,
            -application.evaluation_summary.evaluated_count,
            application.applicant.business_name.casefold(),
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
