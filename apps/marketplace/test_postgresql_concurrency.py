import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from apps.corporate.models import Organization
from apps.evaluation.application.exceptions import (
    ChallengeEvaluationValidationError,
)
from apps.evaluation.application.services import start_challenge_evaluation
from apps.evaluation.models import (
    ChallengeEvaluationRoleAssignment,
    ChallengeTimelineEntry,
)
from apps.marketplace.application.applications import (
    submit_challenge_application,
)
from apps.marketplace.application.challenges import (
    close_challenge,
    publish_challenge,
)
from apps.marketplace.application.commands import (
    PublishChallengeCommand,
    SubmitApplicationCommand,
)
from apps.marketplace.application.exceptions import (
    DuplicateChallengeApplicationError,
)
from apps.marketplace.models import (
    Application,
    Challenge,
    ChallengeCategory,
    ChallengeLifecycleEvent,
)
from apps.notifications.models import Notification


@unittest.skipUnless(
    connection.vendor == "postgresql",
    "Estas pruebas de carrera requieren PostgreSQL.",
)
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class PostgreSQLConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.publisher = Organization.objects.create(
            tax_id="900991001",
            business_name="Convocante concurrencia",
            chamber_of_commerce_record="CC-CONC-1",
            role=Organization.MarketRole.DEMAND_SIDE,
            contact_email="convocante-concurrencia@example.com",
            contact_phone="3000000011",
        )
        self.applicant = Organization.objects.create(
            tax_id="900991002",
            business_name="Proponente concurrencia",
            chamber_of_commerce_record="CC-CONC-2",
            role=Organization.MarketRole.SUPPLY_SIDE,
            contact_email="proponente-concurrencia@example.com",
            contact_phone="3000000012",
        )
        User = get_user_model()
        self.publisher_users = [
            User.objects.create_user(
                username=f"publisher_concurrency_{position}",
                email=f"publisher-concurrency-{position}@example.com",
                password="ClaveSegura123",
                organization=self.publisher,
                is_email_verified=True,
            )
            for position in (1, 2)
        ]
        self.applicant_user = User.objects.create_user(
            username="applicant_concurrency",
            email="applicant-concurrency@example.com",
            password="ClaveSegura123",
            organization=self.applicant,
            is_email_verified=True,
        )
        self.category = ChallengeCategory.objects.create(
            name="Concurrencia PostgreSQL",
            slug="concurrencia-postgresql",
            position=1001,
        )
        self.challenge = publish_challenge(
            publisher=self.publisher,
            command=PublishChallengeCommand(
                title="Desafío de concurrencia",
                description="Valida transiciones simultáneas.",
                evaluation_criteria=("Viabilidad técnica | 70\nValor económico de la oferta | 30"),
                application_deadline=(timezone.localdate() + timedelta(days=10)),
                budget_amount=Decimal("1000000.00"),
                budget_currency=Challenge.Currency.COP,
                category_ids=(self.category.pk,),
            ),
            actor=self.publisher_users[0],
        )

    @staticmethod
    def _submission_command():
        return SubmitApplicationCommand(
            problem_understanding="Entendimiento completo.",
            proposed_solution="Solución viable.",
            capabilities_evidence="Evidencia verificable.",
            execution_plan="Plan con hitos.",
            offered_amount=Decimal("900000.00"),
            offer_currency=Challenge.Currency.COP,
            estimated_duration_days=90,
        )

    @staticmethod
    def _postgres_backend_pid():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            return cursor.fetchone()[0]

    def _results_without_unhandled_exceptions(self, futures):
        results = []
        for future in futures:
            try:
                results.append(future.result(timeout=30))
            except Exception as exc:  # pragma: no cover - assertion diagnostic
                self.fail(
                    "Una transición concurrente filtró una excepción no "
                    f"manejada que podría convertirse en HTTP 500: {exc!r}"
                )
        return results

    def _submit_from_separate_connection(self, barrier):
        close_old_connections()
        try:
            challenge = Challenge.objects.get(pk=self.challenge.pk)
            applicant = Organization.objects.get(pk=self.applicant.pk)
            actor = get_user_model().objects.get(pk=self.applicant_user.pk)
            backend_pid = self._postgres_backend_pid()
            barrier.wait(timeout=10)
            try:
                submit_challenge_application(
                    challenge=challenge,
                    applicant=applicant,
                    command=self._submission_command(),
                    actor=actor,
                )
            except DuplicateChallengeApplicationError:
                return "duplicate", backend_pid
            return "submitted", backend_pid
        finally:
            connection.close()

    def _start_evaluation_from_separate_connection(self, barrier, actor_id):
        close_old_connections()
        try:
            challenge = Challenge.objects.get(pk=self.challenge.pk)
            actor = get_user_model().objects.get(pk=actor_id)
            backend_pid = self._postgres_backend_pid()
            barrier.wait(timeout=10)
            try:
                start_challenge_evaluation(
                    challenge=challenge,
                    actor=actor,
                )
            except ChallengeEvaluationValidationError as exc:
                return "rejected", actor_id, tuple(exc.messages), backend_pid
            return "started", actor_id, (), backend_pid
        finally:
            connection.close()

    def test_concurrent_submission_creates_exactly_one_application(self):
        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    self._submit_from_separate_connection,
                    barrier,
                )
                for _ in range(2)
            ]
            results = self._results_without_unhandled_exceptions(futures)

        self.assertCountEqual(
            [result[0] for result in results],
            ["submitted", "duplicate"],
        )
        self.assertEqual(len({result[1] for result in results}), 2)
        application = Application.objects.get(
            challenge=self.challenge,
            applicant=self.applicant,
        )
        self.assertEqual(application.status, Application.Status.SUBMITTED)
        self.assertEqual(
            self.challenge.lifecycle_events.filter(
                event_type=ChallengeLifecycleEvent.EventType.PUBLISHED,
            ).count(),
            1,
        )

    def test_concurrent_evaluation_start_has_one_winner_and_one_event(self):
        submit_challenge_application(
            challenge=self.challenge,
            applicant=self.applicant,
            command=self._submission_command(),
            actor=self.applicant_user,
        )
        close_challenge(
            challenge=self.challenge,
            actor=self.publisher_users[0],
            reason="Cierre para prueba concurrente.",
        )
        ChallengeEvaluationRoleAssignment.objects.create(
            challenge=self.challenge,
            user=self.publisher_users[0],
            role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR,
        )
        ChallengeEvaluationRoleAssignment.objects.create(
            challenge=self.challenge,
            user=self.publisher_users[0],
            role=ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR,
        )

        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    self._start_evaluation_from_separate_connection,
                    barrier,
                    actor.pk,
                )
                for actor in self.publisher_users
            ]
            results = self._results_without_unhandled_exceptions(futures)

        self.assertCountEqual(
            [result[0] for result in results],
            ["started", "rejected"],
        )
        self.assertEqual(len({result[3] for result in results}), 2)
        rejected_result = next(result for result in results if result[0] == "rejected")
        self.assertIn(
            "Solo los desafíos con recepción cerrada pueden pasar a evaluación.",
            rejected_result[2],
        )

        self.challenge.refresh_from_db()
        self.assertEqual(
            self.challenge.status,
            Challenge.Status.UNDER_EVALUATION,
        )
        timeline_entry = ChallengeTimelineEntry.objects.get(
            challenge=self.challenge,
            event_type=ChallengeTimelineEntry.EventType.EVALUATION_STARTED,
        )
        winning_actor_id = next(result[1] for result in results if result[0] == "started")
        self.assertEqual(timeline_entry.actor_id, winning_actor_id)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.applicant_user,
                kind=Notification.Kind.EVALUATION_STARTED,
            ).count(),
            1,
        )
