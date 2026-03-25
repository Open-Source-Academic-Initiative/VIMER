from apps.marketplace.models import Application, Challenge


def build_challenge_application_blind_reference_map(
    challenge: Challenge,
) -> dict[int, str]:
    application_ids = list(
        challenge.applications.order_by("applied_at", "pk").values_list("pk", flat=True)
    )
    width = max(2, len(str(len(application_ids) or 1)))
    return {
        application_id: f"Propuesta {position:0{width}d}"
        for position, application_id in enumerate(application_ids, start=1)
    }


def get_application_blind_reference(application: Application) -> str:
    return build_challenge_application_blind_reference_map(application.challenge).get(
        application.pk,
        f"Propuesta #{application.pk}",
    )
