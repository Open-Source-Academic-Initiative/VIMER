from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.corporate.models import Organization
from apps.evaluation.application.commands import (
    AwardDecisionCommand,
    CriterionAssessmentInput,
    EvaluateApplicationCommand,
)
from apps.evaluation.application.services import (
    adjudicate_challenge,
    evaluate_application_by_criteria,
    start_challenge_evaluation,
)
from apps.evaluation.models import ChallengeEvaluationRoleAssignment
from apps.marketplace.models import Application, Challenge
from apps.notifications.application.services import mark_all_notifications_as_read
from apps.notifications.models import Notification


class NotificationEventIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publisher = Organization.objects.create(
            tax_id="930000001",
            business_name="Solicitante Notifica",
            chamber_of_commerce_record="CC-NOTIF-1",
            role="DEMAND_SIDE",
            contact_email="solicitante-notifica@example.com",
            contact_phone="3005550001",
        )
        cls.provider = Organization.objects.create(
            tax_id="930000002",
            business_name="Proveedor Notifica",
            chamber_of_commerce_record="CC-NOTIF-2",
            role="SUPPLY_SIDE",
            contact_email="proveedor-notifica@example.com",
            contact_phone="3005550002",
        )
        cls.other_provider = Organization.objects.create(
            tax_id="930000003",
            business_name="Proveedor Alterno",
            chamber_of_commerce_record="CC-NOTIF-3",
            role="SUPPLY_SIDE",
            contact_email="proveedor-alterno@example.com",
            contact_phone="3005550003",
        )
        User = get_user_model()
        cls.publisher_user = User.objects.create_user(
            username="publisher_notifications",
            email="publisher-notifications@example.com",
            password="ClaveSegura123",
            organization=cls.publisher,
        )
        cls.publisher_observer_user = User.objects.create_user(
            username="publisher_observer_notifications",
            email="publisher-observer-notifications@example.com",
            password="ClaveSegura123",
            organization=cls.publisher,
        )
        cls.provider_user = User.objects.create_user(
            username="provider_notifications",
            email="provider-notifications@example.com",
            password="ClaveSegura123",
            organization=cls.provider,
        )
        cls.other_provider_user = User.objects.create_user(
            username="other_provider_notifications",
            email="other-provider-notifications@example.com",
            password="ClaveSegura123",
            organization=cls.other_provider,
        )
        cls.challenge = Challenge.objects.create(
            publisher=cls.publisher,
            title="Challenge notifications",
            description="Description",
            evaluation_criteria="Experiencia, viabilidad técnica y plan de entrega.",
            application_deadline=timezone.localdate() + timedelta(days=7),
        )
        cls.application = Application.objects.create(
            challenge=cls.challenge,
            applicant=cls.provider,
            proposal_text="Resumen",
            problem_understanding="Entendimiento",
            proposed_solution="Solución",
            capabilities_evidence="Capacidades",
            execution_plan="Plan",
        )
        cls.other_application = Application.objects.create(
            challenge=cls.challenge,
            applicant=cls.other_provider,
            proposal_text="Resumen alterno",
            problem_understanding="Otro entendimiento",
            proposed_solution="Otra solución",
            capabilities_evidence="Otras capacidades",
            execution_plan="Otro plan",
        )
        ChallengeEvaluationRoleAssignment.objects.create(
            challenge=cls.challenge,
            user=cls.publisher_user,
            role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR,
        )
        ChallengeEvaluationRoleAssignment.objects.create(
            challenge=cls.challenge,
            user=cls.publisher_user,
            role=ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR,
        )
        ChallengeEvaluationRoleAssignment.objects.create(
            challenge=cls.challenge,
            user=cls.publisher_observer_user,
            role=ChallengeEvaluationRoleAssignment.Role.OBSERVER,
        )

    def build_complete_evaluation_command(self, application: Application | None = None):
        self.challenge.sync_evaluation_criteria_items()
        target_application = application or self.application
        return EvaluateApplicationCommand(
            application_id=target_application.pk,
            assessments=tuple(
                CriterionAssessmentInput(
                    criterion_id=criterion.pk,
                    score=4,
                    comment=f"Comentario de evaluación para {criterion.label}.",
                )
                for criterion in self.challenge.evaluation_criteria_items.order_by("position")
            ),
        )

    def setUp(self):
        self.publisher = Organization.objects.get(pk=self.publisher.pk)
        self.provider = Organization.objects.get(pk=self.provider.pk)
        self.other_provider = Organization.objects.get(pk=self.other_provider.pk)
        User = get_user_model()
        self.publisher_user = User.objects.get(pk=self.publisher_user.pk)
        self.publisher_observer_user = User.objects.get(
            pk=self.publisher_observer_user.pk
        )
        self.provider_user = User.objects.get(pk=self.provider_user.pk)
        self.other_provider_user = User.objects.get(pk=self.other_provider_user.pk)
        self.challenge = Challenge.objects.get(pk=self.challenge.pk)
        self.application = Application.objects.get(pk=self.application.pk)
        self.other_application = Application.objects.get(pk=self.other_application.pk)

    def test_start_evaluation_creates_notifications_for_applicant_members(self):
        with self.captureOnCommitCallbacks(execute=True):
            start_challenge_evaluation(
                challenge=self.challenge,
                actor=self.publisher_user,
            )

        self.assertEqual(
            Notification.objects.filter(
                kind=Notification.Kind.EVALUATION_STARTED
            ).count(),
            2,
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.provider_user,
                title="Tu propuesta entró en evaluación",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.other_provider_user,
                title="Tu propuesta entró en evaluación",
            ).exists()
        )

    def test_award_creates_notifications_for_publisher_and_applicants(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()
        evaluate_application_by_criteria(
            challenge=self.challenge,
            application=self.application,
            actor=self.publisher_user,
            command=self.build_complete_evaluation_command(self.application),
        )
        evaluate_application_by_criteria(
            challenge=self.challenge,
            application=self.other_application,
            actor=self.publisher_user,
            command=self.build_complete_evaluation_command(self.other_application),
        )

        with self.captureOnCommitCallbacks(execute=True):
            adjudicate_challenge(
                challenge=self.challenge,
                actor=self.publisher_user,
                command=AwardDecisionCommand(
                    winning_application_id=self.application.pk,
                    comment="Ganadora por mayor ajuste técnico.",
                ),
            )

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.publisher_user,
                title="Registraste una adjudicación",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.provider_user,
                title="Tu propuesta fue adjudicada",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.other_provider_user,
                title="Se registró la adjudicación del desafío",
            ).exists()
        )

    def test_application_evaluation_creates_notification_for_applicant_members(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()

        with self.captureOnCommitCallbacks(execute=True):
            evaluate_application_by_criteria(
                challenge=self.challenge,
                application=self.application,
                actor=self.publisher_user,
                command=self.build_complete_evaluation_command(),
            )

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.provider_user,
                kind=Notification.Kind.APPLICATION_EVALUATED,
                title="Tu propuesta recibió una evaluación",
            ).exists()
        )
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.other_provider_user,
                kind=Notification.Kind.APPLICATION_EVALUATED,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.publisher_observer_user,
                kind=Notification.Kind.APPLICATION_EVALUATED,
                title="Se registró actividad de evaluación",
            ).exists()
        )
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.publisher_user,
                kind=Notification.Kind.APPLICATION_EVALUATED,
                title="Se registró actividad de evaluación",
            ).exists()
        )

    def test_mark_all_notifications_as_read_updates_unread_notifications(self):
        Notification.objects.create(
            recipient=self.provider_user,
            kind=Notification.Kind.EVALUATION_STARTED,
            title="Pendiente",
            body="Mensaje",
        )
        Notification.objects.create(
            recipient=self.provider_user,
            kind=Notification.Kind.CHALLENGE_AWARDED,
            title="Pendiente 2",
            body="Mensaje 2",
        )

        updated = mark_all_notifications_as_read(recipient=self.provider_user)

        self.assertEqual(updated, 2)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.provider_user,
                read_at__isnull=True,
            ).count(),
            0,
        )


class NotificationFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        organization = Organization.objects.create(
            tax_id="940000001",
            business_name="Organizacion Flow Notif",
            chamber_of_commerce_record="CC-NOTIF-F1",
            role="SUPPLY_SIDE",
            contact_email="flow-notif@example.com",
            contact_phone="3006660001",
        )
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="flow_notifications",
            email="flow-notifications@example.com",
            password="ClaveSegura123",
            organization=organization,
        )
        cls.notification = Notification.objects.create(
            recipient=cls.user,
            kind=Notification.Kind.EVALUATION_STARTED,
            title="Nueva notificación",
            body="El desafío pasó a evaluación.",
            link="/marketplace/challenge/1/",
        )

    def setUp(self):
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.notification = Notification.objects.get(pk=self.notification.pk)

    def test_notifications_list_view_shows_unread_notifications(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("notifications:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nueva notificación")
        self.assertContains(response, "No leída")

    def test_mark_all_read_view_marks_notifications_as_read(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("notifications:mark-all-read"))

        self.assertRedirects(response, reverse("notifications:list"))
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.user,
                read_at__isnull=True,
            ).exists()
        )

    def test_base_navigation_shows_unread_notification_count(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("notifications:list"))

        self.assertContains(response, "Notificaciones (1)")
