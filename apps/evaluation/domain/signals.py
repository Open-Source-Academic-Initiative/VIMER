from django.db import transaction
from django.dispatch import Signal

from apps.evaluation.domain.events import (
    ApplicationEvaluationRecorded,
    ChallengeAwarded,
    ChallengeEvaluationStarted,
)

challenge_evaluation_started = Signal()
challenge_awarded = Signal()
application_evaluation_recorded = Signal()


def publish_challenge_evaluation_started(event: ChallengeEvaluationStarted) -> None:
    transaction.on_commit(
        lambda: challenge_evaluation_started.send(
            sender=ChallengeEvaluationStarted,
            event=event,
        )
    )


def publish_challenge_awarded(event: ChallengeAwarded) -> None:
    transaction.on_commit(
        lambda: challenge_awarded.send(
            sender=ChallengeAwarded,
            event=event,
        )
    )


def publish_application_evaluation_recorded(
    event: ApplicationEvaluationRecorded,
) -> None:
    transaction.on_commit(
        lambda: application_evaluation_recorded.send(
            sender=ApplicationEvaluationRecorded,
            event=event,
        )
    )
