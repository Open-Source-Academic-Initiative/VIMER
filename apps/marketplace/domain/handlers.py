from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.marketplace.models import ApplicationAttachment, ChallengeAttachment


def _delete_committed_file(instance) -> None:
    if not instance.file:
        return
    storage = instance.file.storage
    file_name = instance.file.name
    transaction.on_commit(lambda: storage.delete(file_name))


@receiver(
    post_delete,
    sender=ChallengeAttachment,
    dispatch_uid="marketplace.delete_committed_challenge_attachment_file",
)
def delete_challenge_attachment_file(sender, instance, **kwargs):
    _delete_committed_file(instance)


@receiver(
    post_delete,
    sender=ApplicationAttachment,
    dispatch_uid="marketplace.delete_committed_application_attachment_file",
)
def delete_application_attachment_file(sender, instance, **kwargs):
    _delete_committed_file(instance)
