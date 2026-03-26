from django.urls import reverse
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
from apps.evaluation.models import AwardDecision
from apps.evaluation.models import ChallengeEvaluationRoleAssignment
from apps.identity.models import User
from apps.marketplace.models import Application, Challenge
from apps.notifications.models import Notification


def _build_challenge_link(challenge_id: int) -> str:
    return reverse("marketplace:challenge-detail", args=[challenge_id])


@receiver(
    challenge_evaluation_started,
    sender=ChallengeEvaluationStarted,
    dispatch_uid="notifications.on_challenge_evaluation_started",
)
def create_notifications_for_evaluation_started(sender, *, event, **kwargs):
    challenge = Challenge.objects.prefetch_related(
        "applications__applicant__members"
    ).get(pk=event.challenge_id)
    recipient_ids = sorted(
        {
            member.pk
            for application in challenge.applications.all()
            for member in application.applicant.members.all()
        }
    )
    if not recipient_ids:
        return

    recipients = User.objects.filter(pk__in=recipient_ids)
    notifications = [
        Notification(
            recipient=recipient,
            kind=Notification.Kind.EVALUATION_STARTED,
            title="Tu propuesta entró en evaluación",
            body=(
                f"El desafío '{challenge.title}' pasó a evaluación."
            ),
            link=_build_challenge_link(challenge.pk),
        )
        for recipient in recipients
    ]
    Notification.objects.bulk_create(notifications)


@receiver(
    challenge_awarded,
    sender=ChallengeAwarded,
    dispatch_uid="notifications.on_challenge_awarded",
)
def create_notifications_for_challenge_awarded(sender, *, event, **kwargs):
    challenge = Challenge.objects.select_related("publisher").prefetch_related(
        "publisher__members",
        "applications__applicant__members",
    ).get(pk=event.challenge_id)
    decision = AwardDecision.objects.select_related(
        "winning_application__applicant"
    ).get(pk=event.award_decision_id)
    winning_org = decision.winning_application.applicant

    notifications = []

    for recipient in challenge.publisher.members.all():
        notifications.append(
            Notification(
                recipient=recipient,
                kind=Notification.Kind.CHALLENGE_AWARDED,
                title="Registraste una adjudicación",
                body=(
                    f"El desafío '{challenge.title}' fue adjudicado a "
                    f"'{winning_org.business_name}'."
                ),
                link=_build_challenge_link(challenge.pk),
            )
        )

    applicant_orgs = {
        application.applicant_id: application.applicant
        for application in challenge.applications.all()
    }
    for organization in applicant_orgs.values():
        for recipient in organization.members.all():
            organization_won = organization.pk == winning_org.pk
            notifications.append(
                Notification(
                    recipient=recipient,
                    kind=Notification.Kind.CHALLENGE_AWARDED,
                    title=(
                        "Tu propuesta fue adjudicada"
                        if organization_won
                        else "Se registró la adjudicación del desafío"
                    ),
                    body=(
                        f"El desafío '{challenge.title}' fue adjudicado a tu organización."
                        if organization_won
                        else (
                            f"El desafío '{challenge.title}' fue adjudicado a "
                            f"'{winning_org.business_name}'."
                        )
                    ),
                    link=_build_challenge_link(challenge.pk),
                )
            )

    if notifications:
        Notification.objects.bulk_create(notifications)


@receiver(
    application_evaluation_recorded,
    sender=ApplicationEvaluationRecorded,
    dispatch_uid="notifications.on_application_evaluation_recorded",
)
def create_notifications_for_application_evaluated(sender, *, event, **kwargs):
    application = Application.objects.select_related(
        "challenge",
        "applicant",
    ).prefetch_related(
        "applicant__members",
        "challenge__evaluation_role_assignments__user",
    ).get(pk=event.application_id)
    applicant_ranking_fragment = (
        f"posición competitiva actual #{event.ranking_position}."
        if event.ranking_position is not None
        else "todavía fuera del ranking competitivo."
    )
    notifications = [
        Notification(
            recipient=recipient,
            kind=Notification.Kind.APPLICATION_EVALUATED,
            title="Tu propuesta recibió una evaluación",
            body=(
                f"Tu propuesta para '{application.challenge.title}' quedó con "
                f"{event.evaluated_count}/{event.criteria_total} criterios evaluados, "
                f"{event.assessment_count} evaluaciones registradas, "
                f"promedio {event.average_score:.2f}/5 y {applicant_ranking_fragment}"
            ),
            link=_build_challenge_link(application.challenge_id),
        )
        for recipient in application.applicant.members.all()
    ]
    team_recipient_ids = sorted(
        {
            assignment.user_id
            for assignment in application.challenge.evaluation_role_assignments.all()
            if assignment.role
            in {
                ChallengeEvaluationRoleAssignment.Role.EVALUATOR,
                ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR,
                ChallengeEvaluationRoleAssignment.Role.OBSERVER,
            }
            and assignment.user_id != event.evaluated_by_user_id
        }
    )
    if team_recipient_ids:
        for recipient in User.objects.filter(pk__in=team_recipient_ids):
            notifications.append(
                Notification(
                    recipient=recipient,
                    kind=Notification.Kind.APPLICATION_EVALUATED,
                    title="Se registró actividad de evaluación",
                    body=(
                        f"{event.blind_reference} quedó con "
                        f"{event.evaluated_count}/{event.criteria_total} criterios cubiertos, "
                        f"{event.assessment_count} evaluaciones registradas y "
                        f"promedio {event.average_score:.2f}/5."
                    ),
                    link=_build_challenge_link(application.challenge_id),
                )
            )
    if notifications:
        Notification.objects.bulk_create(notifications)
