from django.db import transaction
from django.dispatch import Signal

from apps.marketplace.domain.events import ChallengeLifecycleChanged


challenge_lifecycle_changed = Signal()


def publish_challenge_lifecycle_changed(
    event: ChallengeLifecycleChanged,
) -> None:
    transaction.on_commit(
        lambda: challenge_lifecycle_changed.send(
            sender=ChallengeLifecycleChanged,
            event=event,
        )
    )
