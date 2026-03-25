from django.dispatch import receiver

from apps.evaluation.domain.events import (
    ApplicationEvaluationRecorded,
    ChallengeAwarded,
    ChallengeEvaluationStarted,
)
from apps.evaluation.domain.signals import (
    application_evaluation_recorded,
    challenge_awarded,
    challenge_evaluation_started,
)
from apps.evaluation.models import ChallengeTimelineEntry


@receiver(
    challenge_evaluation_started,
    sender=ChallengeEvaluationStarted,
    dispatch_uid="evaluation.record_challenge_evaluation_started",
)
def record_challenge_evaluation_started(sender, *, event, **kwargs):
    ChallengeTimelineEntry.objects.create(
        challenge_id=event.challenge_id,
        event_type=ChallengeTimelineEntry.EventType.EVALUATION_STARTED,
        actor_id=event.started_by_user_id,
        description="La organización publicadora inició la evaluación del desafío.",
        occurred_at=event.occurred_at,
    )


@receiver(
    challenge_awarded,
    sender=ChallengeAwarded,
    dispatch_uid="evaluation.record_challenge_awarded",
)
def record_challenge_awarded(sender, *, event, **kwargs):
    ChallengeTimelineEntry.objects.create(
        challenge_id=event.challenge_id,
        event_type=ChallengeTimelineEntry.EventType.CHALLENGE_AWARDED,
        actor_id=event.decided_by_user_id,
        award_decision_id=event.award_decision_id,
        description="Se registró la adjudicación del desafío.",
        occurred_at=event.occurred_at,
    )


@receiver(
    application_evaluation_recorded,
    sender=ApplicationEvaluationRecorded,
    dispatch_uid="evaluation.record_application_evaluation_recorded",
)
def record_application_evaluation_recorded(sender, *, event, **kwargs):
    ChallengeTimelineEntry.objects.create(
        challenge_id=event.challenge_id,
        event_type=ChallengeTimelineEntry.EventType.APPLICATION_EVALUATED,
        actor_id=event.evaluated_by_user_id,
        description=(
            f"Se registró actividad de evaluación sobre {event.blind_reference}. "
            f"Cobertura actual: {event.evaluated_count}/{event.criteria_total} criterios. "
            f"Evaluaciones acumuladas: {event.assessment_count}. "
            f"Promedio actual: {event.average_score:.2f}/5."
        ),
        occurred_at=event.occurred_at,
    )
