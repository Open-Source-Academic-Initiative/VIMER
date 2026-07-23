from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.corporate.models import Organization
from apps.evaluation.application.exceptions import (
    ChallengeEvaluationValidationError,
)
from apps.evaluation.application.services import start_challenge_evaluation
from apps.evaluation.models import ChallengeEvaluationRoleAssignment
from apps.marketplace.application.applications import (
    submit_challenge_application,
)
from apps.marketplace.application.challenges import (
    cancel_challenge,
    close_challenge,
    close_expired_challenge,
    create_challenge_draft,
    declare_challenge_deserted,
    publish_challenge,
)
from apps.marketplace.application.commands import (
    PublishChallengeCommand,
    SubmitApplicationCommand,
)
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    ChallengeLifecycleValidationError,
)
from apps.marketplace.models import (
    Application,
    Challenge,
    ChallengeCategory,
    ChallengeLifecycleEvent,
)
from apps.notifications.models import Notification


class BusinessRemediationTests(TestCase):
    def setUp(self):
        self.publisher = Organization.objects.create(
            tax_id="900990001",
            business_name="Convocante remediación",
            chamber_of_commerce_record="CC-REM-1",
            role=Organization.MarketRole.DEMAND_SIDE,
            contact_email="convocante-remediacion@example.com",
            contact_phone="3000000001",
        )
        self.applicant = Organization.objects.create(
            tax_id="900990002",
            business_name="Proponente remediación",
            chamber_of_commerce_record="CC-REM-2",
            role=Organization.MarketRole.SUPPLY_SIDE,
            contact_email="proponente-remediacion@example.com",
            contact_phone="3000000002",
        )
        User = get_user_model()
        self.publisher_user = User.objects.create_user(
            username="publisher_remediation",
            email="publisher-remediation@example.com",
            password="ClaveSegura123",
            organization=self.publisher,
            is_email_verified=True,
        )
        self.applicant_user = User.objects.create_user(
            username="applicant_remediation",
            email="applicant-remediation@example.com",
            password="ClaveSegura123",
            organization=self.applicant,
            is_email_verified=True,
        )
        self.category = ChallengeCategory.objects.create(
            name="Remediación",
            slug="remediacion",
            position=999,
        )

    def publication_command(self, *, title="Desafío remediado", deadline=None):
        return PublishChallengeCommand(
            title=title,
            description="Necesidad empresarial verificable.",
            evaluation_criteria=(
                "Viabilidad técnica | 70\n"
                "Valor económico de la oferta | 30"
            ),
            application_deadline=(
                deadline
                or timezone.localdate() + timedelta(days=10)
            ),
            budget_amount=Decimal("1000000.00"),
            budget_currency=Challenge.Currency.COP,
            category_ids=(self.category.pk,),
        )

    def publish(self, *, title="Desafío remediado", deadline=None):
        return publish_challenge(
            publisher=self.publisher,
            command=self.publication_command(
                title=title,
                deadline=deadline,
            ),
            actor=self.publisher_user,
        )

    def submission_command(
        self,
        *,
        offered_amount=Decimal("900000.00"),
        currency=Challenge.Currency.COP,
    ):
        return SubmitApplicationCommand(
            problem_understanding="Entendimiento completo.",
            proposed_solution="Solución viable.",
            capabilities_evidence="Evidencia verificable.",
            execution_plan="Plan con hitos.",
            offered_amount=offered_amount,
            offer_currency=currency,
            estimated_duration_days=90,
        )

    def test_default_is_draft_and_weighted_parser_preserves_labels(self):
        challenge = Challenge.objects.create(
            publisher=self.publisher,
            title="Parser ponderado",
            description="Prueba",
            evaluation_criteria=(
                "5G readiness\n"
                ".NET expertise\n"
                "-\n"
                "Valor económico de la oferta | 20"
            ),
        )

        criteria = list(
            challenge.evaluation_criteria_items.order_by("position")
        )

        self.assertEqual(challenge.status, Challenge.Status.DRAFT)
        self.assertEqual(
            [criterion.label for criterion in criteria],
            ["5G readiness", ".NET expertise", "Valor económico de la oferta"],
        )
        self.assertEqual(
            sum(criterion.weight for criterion in criteria),
            Decimal("100.00"),
        )
        self.assertEqual(
            criteria[-1].criterion_type,
            criteria[-1].CriterionType.ECONOMIC,
        )

    def test_offer_must_respect_budget_and_currency(self):
        challenge = self.publish()

        with self.assertRaises(ChallengeApplicationValidationError):
            submit_challenge_application(
                challenge=challenge,
                applicant=self.applicant,
                command=self.submission_command(
                    offered_amount=Decimal("1000000.01")
                ),
                actor=self.applicant_user,
            )

        with self.assertRaises(ChallengeApplicationValidationError):
            submit_challenge_application(
                challenge=challenge,
                applicant=self.applicant,
                command=self.submission_command(
                    currency=Challenge.Currency.USD
                ),
                actor=self.applicant_user,
            )

        application = submit_challenge_application(
            challenge=challenge,
            applicant=self.applicant,
            command=self.submission_command(),
            actor=self.applicant_user,
        )
        self.assertEqual(application.offered_amount, Decimal("900000.00"))
        self.assertEqual(application.estimated_duration_days, 90)

    def test_draft_can_be_edited_and_published_over_http(self):
        challenge = create_challenge_draft(
            publisher=self.publisher,
            command=self.publication_command(title="Borrador inicial"),
            actor=self.publisher_user,
        )
        self.client.force_login(self.publisher_user)

        response = self.client.post(
            reverse("marketplace:challenge-edit", args=[challenge.pk]),
            {
                "title": "Borrador actualizado",
                "description": "Contenido revisado.",
                "evaluation_criteria": (
                    "Capacidad técnica | 60\n"
                    "Valor económico de la oferta | 40"
                ),
                "application_deadline": (
                    timezone.localdate() + timedelta(days=20)
                ),
                "budget_amount": "1200000.00",
                "budget_currency": Challenge.Currency.COP,
                "categories": [self.category.pk],
                "intent": "publish",
            },
        )

        self.assertRedirects(
            response,
            reverse("marketplace:challenge-detail", args=[challenge.pk]),
        )
        challenge.refresh_from_db()
        self.assertEqual(challenge.title, "Borrador actualizado")
        self.assertEqual(challenge.status, Challenge.Status.PUBLISHED)
        self.assertEqual(
            list(
                challenge.lifecycle_events.values_list(
                    "event_type",
                    flat=True,
                )
            )[::-1],
            [
                ChallengeLifecycleEvent.EventType.DRAFT_CREATED,
                ChallengeLifecycleEvent.EventType.DRAFT_UPDATED,
                ChallengeLifecycleEvent.EventType.PUBLISHED,
            ],
        )

    def test_manual_transitions_are_audited_and_idempotent(self):
        challenge = self.publish(title="Cierre y desierto")
        close_challenge(
            challenge=challenge,
            actor=self.publisher_user,
            reason="Cierre anticipado aprobado.",
        )

        with self.assertRaises(ChallengeLifecycleValidationError):
            close_challenge(
                challenge=challenge,
                actor=self.publisher_user,
                reason="Segundo cierre.",
            )

        challenge.refresh_from_db()
        with self.captureOnCommitCallbacks(execute=True):
            declare_challenge_deserted(
                challenge=challenge,
                actor=self.publisher_user,
                reason="No existen propuestas elegibles.",
            )
        cancelled = self.publish(title="Cancelación")
        with self.captureOnCommitCallbacks(execute=True):
            cancel_challenge(
                challenge=cancelled,
                actor=self.publisher_user,
                reason="Cambio documentado de prioridad.",
            )

        self.assertEqual(
            challenge.lifecycle_events.filter(
                event_type=ChallengeLifecycleEvent.EventType.CLOSED
            ).count(),
            1,
        )
        challenge.refresh_from_db()
        cancelled.refresh_from_db()
        self.assertEqual(challenge.status, Challenge.Status.DESERTED)
        self.assertEqual(cancelled.status, Challenge.Status.CANCELLED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.publisher_user,
                kind=Notification.Kind.CHALLENGE_DESERTED,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.publisher_user,
                kind=Notification.Kind.CHALLENGE_CANCELLED,
            ).exists()
        )

    def test_automatic_deadline_close_is_idempotent_and_notifies(self):
        challenge = self.publish(title="Cierre automático")
        submit_challenge_application(
            challenge=challenge,
            applicant=self.applicant,
            command=self.submission_command(),
            actor=self.applicant_user,
        )
        Challenge.objects.filter(pk=challenge.pk).update(
            application_deadline=timezone.localdate() - timedelta(days=1)
        )

        with self.captureOnCommitCallbacks(execute=True):
            first_result = close_expired_challenge(
                challenge_id=challenge.pk
            )
        second_result = close_expired_challenge(challenge_id=challenge.pk)

        self.assertIsNotNone(first_result)
        self.assertIsNone(second_result)
        event = challenge.lifecycle_events.get(
            event_type=ChallengeLifecycleEvent.EventType.CLOSED
        )
        self.assertTrue(event.is_automatic)
        self.assertIsNone(event.actor)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.applicant_user,
                kind=Notification.Kind.CHALLENGE_CLOSED,
            ).exists()
        )

    def test_management_command_can_be_repeated_safely(self):
        challenge = self.publish(title="Comando idempotente")
        Challenge.objects.filter(pk=challenge.pk).update(
            application_deadline=timezone.localdate() - timedelta(days=1)
        )

        call_command("close_expired_challenges")
        call_command("close_expired_challenges")

        self.assertEqual(
            challenge.lifecycle_events.filter(
                event_type=ChallengeLifecycleEvent.EventType.CLOSED
            ).count(),
            1,
        )

    def test_evaluation_start_requires_closed_state_and_is_idempotent(self):
        challenge = self.publish(title="Evaluación serializada")
        submit_challenge_application(
            challenge=challenge,
            applicant=self.applicant,
            command=self.submission_command(),
            actor=self.applicant_user,
        )
        ChallengeEvaluationRoleAssignment.objects.create(
            challenge=challenge,
            user=self.publisher_user,
            role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR,
        )
        ChallengeEvaluationRoleAssignment.objects.create(
            challenge=challenge,
            user=self.publisher_user,
            role=ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR,
        )

        with self.assertRaises(ChallengeEvaluationValidationError):
            start_challenge_evaluation(
                challenge=challenge,
                actor=self.publisher_user,
            )

        close_challenge(
            challenge=challenge,
            actor=self.publisher_user,
            reason="Cierre autorizado para evaluar.",
        )
        start_challenge_evaluation(
            challenge=challenge,
            actor=self.publisher_user,
        )
        with self.assertRaises(ChallengeEvaluationValidationError):
            start_challenge_evaluation(
                challenge=challenge,
                actor=self.publisher_user,
            )

        challenge.refresh_from_db()
        self.assertEqual(
            challenge.status,
            Challenge.Status.UNDER_EVALUATION,
        )

    def test_criteria_and_commercial_terms_freeze_after_proposal(self):
        challenge = self.publish(title="Expediente congelado")
        Application.objects.create(
            challenge=challenge,
            applicant=self.applicant,
            status=Application.Status.DRAFT,
        )
        challenge.evaluation_criteria = (
            "Criterio reinterpretado | 100"
        )

        with self.assertRaises(ValidationError):
            challenge.save()
