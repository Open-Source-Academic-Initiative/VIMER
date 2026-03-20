from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.corporate.models import Organization
from apps.evaluation.application.commands import AwardDecisionCommand
from apps.evaluation.application.exceptions import ChallengeEvaluationValidationError
from apps.evaluation.application.services import (
    adjudicate_challenge,
    start_challenge_evaluation,
)
from apps.evaluation.models import AwardDecision
from apps.marketplace.models import Application, Challenge


class EvaluationServiceTests(TestCase):
    def setUp(self):
        self.publisher = Organization.objects.create(
            tax_id="910000001",
            business_name="Solicitante Evaluador",
            chamber_of_commerce_record="CC-EVAL-1",
            role="DEMAND_SIDE",
            contact_email="solicitante-eval@example.com",
            contact_phone="3001110000",
        )
        self.provider = Organization.objects.create(
            tax_id="910000002",
            business_name="Proveedor Evaluado",
            chamber_of_commerce_record="CC-EVAL-2",
            role="SUPPLY_SIDE",
            contact_email="proveedor-eval@example.com",
            contact_phone="3002220000",
        )
        self.other_publisher = Organization.objects.create(
            tax_id="910000003",
            business_name="Otro Solicitante",
            chamber_of_commerce_record="CC-EVAL-3",
            role="DEMAND_SIDE",
            contact_email="otro-solicitante@example.com",
            contact_phone="3003330000",
        )
        User = get_user_model()
        self.publisher_user = User.objects.create_user(
            username="publisher_eval",
            email="publisher-eval@example.com",
            password="ClaveSegura123",
            organization=self.publisher,
        )
        self.other_publisher_user = User.objects.create_user(
            username="other_publisher_eval",
            email="other-publisher-eval@example.com",
            password="ClaveSegura123",
            organization=self.other_publisher,
        )
        self.challenge = Challenge.objects.create(
            publisher=self.publisher,
            title="Challenge under evaluation",
            description="Description",
            application_deadline=timezone.localdate() + timedelta(days=7),
        )
        self.application = Application.objects.create(
            challenge=self.challenge,
            applicant=self.provider,
            proposal_text="Resumen",
            problem_understanding="Entendimiento",
            proposed_solution="Solución",
            capabilities_evidence="Capacidades",
            execution_plan="Plan",
        )

    def test_start_challenge_evaluation_sets_under_evaluation_status(self):
        start_challenge_evaluation(challenge=self.challenge, actor=self.publisher_user)

        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.status, Challenge.Status.UNDER_EVALUATION)

    def test_start_challenge_evaluation_rejects_non_publisher(self):
        with self.assertRaises(ChallengeEvaluationValidationError) as captured:
            start_challenge_evaluation(
                challenge=self.challenge,
                actor=self.other_publisher_user,
            )

        self.assertIn(
            "Solo la organización publicadora puede iniciar la evaluación.",
            captured.exception.messages,
        )

    def test_start_challenge_evaluation_rejects_missing_applications(self):
        self.application.delete()

        with self.assertRaises(ChallengeEvaluationValidationError) as captured:
            start_challenge_evaluation(challenge=self.challenge, actor=self.publisher_user)

        self.assertIn(
            "No puedes iniciar evaluación sin propuestas registradas.",
            captured.exception.messages,
        )

    def test_adjudicate_challenge_creates_decision_and_awards_challenge(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()

        decision = adjudicate_challenge(
            challenge=self.challenge,
            actor=self.publisher_user,
            command=AwardDecisionCommand(
                winning_application_id=self.application.pk,
                comment="La propuesta ofrece el mejor encaje técnico y operativo.",
            ),
        )

        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.status, Challenge.Status.AWARDED)
        self.assertEqual(decision.challenge, self.challenge)
        self.assertEqual(decision.winning_application, self.application)

    def test_adjudicate_challenge_requires_under_evaluation_status(self):
        with self.assertRaises(ChallengeEvaluationValidationError) as captured:
            adjudicate_challenge(
                challenge=self.challenge,
                actor=self.publisher_user,
                command=AwardDecisionCommand(
                    winning_application_id=self.application.pk,
                    comment="Comentario",
                ),
            )

        self.assertIn(
            "Solo los desafíos en evaluación pueden adjudicarse.",
            captured.exception.messages,
        )

    def test_adjudicate_challenge_requires_comment(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()

        with self.assertRaises(ChallengeEvaluationValidationError) as captured:
            adjudicate_challenge(
                challenge=self.challenge,
                actor=self.publisher_user,
                command=AwardDecisionCommand(
                    winning_application_id=self.application.pk,
                    comment="",
                ),
            )

        self.assertIn(
            "Debes registrar un comentario de adjudicación.",
            captured.exception.messages,
        )

    def test_adjudicate_challenge_rejects_second_decision_for_same_challenge(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()
        adjudicate_challenge(
            challenge=self.challenge,
            actor=self.publisher_user,
            command=AwardDecisionCommand(
                winning_application_id=self.application.pk,
                comment="Primera decisión.",
            ),
        )

        with self.assertRaises(ChallengeEvaluationValidationError) as captured:
            adjudicate_challenge(
                challenge=self.challenge,
                actor=self.publisher_user,
                command=AwardDecisionCommand(
                    winning_application_id=self.application.pk,
                    comment="Segunda decisión.",
                ),
            )

        self.assertIn(
            "Solo los desafíos en evaluación pueden adjudicarse.",
            captured.exception.messages,
        )


class EvaluationFlowTests(TestCase):
    def setUp(self):
        self.publisher = Organization.objects.create(
            tax_id="920000001",
            business_name="Solicitante Flow",
            chamber_of_commerce_record="CC-EVAL-F1",
            role="DEMAND_SIDE",
            contact_email="solicitante-flow@example.com",
            contact_phone="3001111111",
        )
        self.provider = Organization.objects.create(
            tax_id="920000002",
            business_name="Proveedor Flow",
            chamber_of_commerce_record="CC-EVAL-F2",
            role="SUPPLY_SIDE",
            contact_email="proveedor-flow@example.com",
            contact_phone="3002222222",
        )
        User = get_user_model()
        self.publisher_user = User.objects.create_user(
            username="publisher_flow",
            email="publisher-flow@example.com",
            password="ClaveSegura123",
            organization=self.publisher,
        )
        self.provider_user = User.objects.create_user(
            username="provider_flow",
            email="provider-flow@example.com",
            password="ClaveSegura123",
            organization=self.provider,
        )
        self.challenge = Challenge.objects.create(
            publisher=self.publisher,
            title="Challenge flow",
            description="Description",
            application_deadline=timezone.localdate() + timedelta(days=7),
        )
        self.application = Application.objects.create(
            challenge=self.challenge,
            applicant=self.provider,
            proposal_text="Resumen",
            problem_understanding="Entendimiento",
            proposed_solution="Solución",
            capabilities_evidence="Capacidades",
            execution_plan="Plan",
        )

    def test_challenge_detail_shows_start_evaluation_action_for_publisher(self):
        self.client.force_login(self.publisher_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Iniciar evaluación")

    def test_start_evaluation_view_redirects_and_updates_status(self):
        self.client.force_login(self.publisher_user)

        response = self.client.post(
            reverse("evaluation:challenge-evaluation-start", args=[self.challenge.pk])
        )

        self.assertRedirects(
            response,
            reverse("marketplace:challenge-detail", args=[self.challenge.pk]),
        )
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.status, Challenge.Status.UNDER_EVALUATION)

    def test_award_decision_view_registers_decision(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()
        self.client.force_login(self.publisher_user)

        response = self.client.post(
            reverse("evaluation:award-decision-create", args=[self.challenge.pk]),
            {
                "winning_application": self.application.pk,
                "comment": "Seleccionada por su solidez técnica.",
            },
        )

        self.assertRedirects(
            response,
            reverse("marketplace:challenge-detail", args=[self.challenge.pk]),
        )
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.status, Challenge.Status.AWARDED)
        self.assertTrue(AwardDecision.objects.filter(challenge=self.challenge).exists())

    def test_provider_cannot_access_award_decision_view(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()
        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("evaluation:award-decision-create", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 403)
