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
from apps.evaluation.application.exceptions import ChallengeEvaluationValidationError
from apps.evaluation.application.queries import (
    build_challenge_application_evaluation_summaries,
)
from apps.evaluation.application.services import (
    adjudicate_challenge,
    evaluate_application_by_criteria,
    start_challenge_evaluation,
)
from apps.evaluation.domain.events import ChallengeAwarded, ChallengeEvaluationStarted
from apps.evaluation.domain.signals import (
    challenge_awarded,
    challenge_evaluation_started,
)
from apps.evaluation.models import (
    ApplicationCriterionEvaluation,
    AwardDecision,
    ChallengeTimelineEntry,
)
from apps.marketplace.models import Application, Challenge


class EvaluationServiceTests(TestCase):
    def build_complete_evaluation_command(self):
        self.challenge.sync_evaluation_criteria_items()
        return EvaluateApplicationCommand(
            application_id=self.application.pk,
            assessments=tuple(
                CriterionAssessmentInput(
                    criterion_id=criterion.pk,
                    score=4,
                    comment=f"Evaluación favorable para {criterion.label}.",
                )
                for criterion in self.challenge.evaluation_criteria_items.order_by("position")
            ),
        )

    def register_complete_evaluation(self):
        return evaluate_application_by_criteria(
            challenge=self.challenge,
            application=self.application,
            actor=self.publisher_user,
            command=self.build_complete_evaluation_command(),
        )

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
            evaluation_criteria="Experiencia, viabilidad técnica y plan de ejecución.",
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

    def test_start_challenge_evaluation_emits_domain_event_after_commit(self):
        received_events = []

        def receiver(sender, event, **kwargs):
            received_events.append(event)

        challenge_evaluation_started.connect(
            receiver,
            dispatch_uid="test_start_challenge_evaluation_event",
            weak=False,
        )
        try:
            with self.captureOnCommitCallbacks(execute=True):
                start_challenge_evaluation(
                    challenge=self.challenge,
                    actor=self.publisher_user,
                )
        finally:
            challenge_evaluation_started.disconnect(
                dispatch_uid="test_start_challenge_evaluation_event"
            )

        self.assertEqual(len(received_events), 1)
        event = received_events[0]
        self.assertIsInstance(event, ChallengeEvaluationStarted)
        self.assertEqual(event.challenge_id, self.challenge.pk)
        self.assertEqual(event.publisher_organization_id, self.publisher.pk)
        self.assertEqual(event.started_by_user_id, self.publisher_user.pk)

    def test_start_challenge_evaluation_records_timeline_entry_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            start_challenge_evaluation(
                challenge=self.challenge,
                actor=self.publisher_user,
            )

        entry = ChallengeTimelineEntry.objects.get(
            challenge=self.challenge,
            event_type=ChallengeTimelineEntry.EventType.EVALUATION_STARTED,
        )
        self.assertEqual(entry.actor, self.publisher_user)
        self.assertEqual(
            entry.description,
            "La organización publicadora inició la evaluación del desafío.",
        )

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

    def test_start_challenge_evaluation_rejects_missing_evaluation_criteria(self):
        self.challenge.evaluation_criteria = ""
        self.challenge.save()

        with self.assertRaises(ChallengeEvaluationValidationError) as captured:
            start_challenge_evaluation(challenge=self.challenge, actor=self.publisher_user)

        self.assertIn(
            "No puedes iniciar evaluación sin criterios de evaluación definidos.",
            captured.exception.messages,
        )

    def test_award_decision_view_shows_structured_evaluation_criteria(self):
        self.challenge.evaluation_criteria = "Capacidad técnica\nExperiencia sectorial"
        self.challenge.save()
        self.challenge.evaluation_criteria_items.create(
            label="Capacidad técnica",
            position=1,
        )
        self.challenge.evaluation_criteria_items.create(
            label="Experiencia sectorial",
            position=2,
        )
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()
        self.client.force_login(self.publisher_user)

        response = self.client.get(
            reverse("evaluation:award-decision-create", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Criterios de evaluación")
        self.assertContains(response, "Capacidad técnica")
        self.assertContains(response, "Experiencia sectorial")

    def test_evaluate_application_by_criteria_creates_assessments(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()

        evaluate_application_by_criteria(
            challenge=self.challenge,
            application=self.application,
            actor=self.publisher_user,
            command=self.build_complete_evaluation_command(),
        )

        self.assertEqual(
            ApplicationCriterionEvaluation.objects.filter(application=self.application).count(),
            1,
        )

    def test_adjudicate_challenge_creates_decision_and_awards_challenge(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()
        self.register_complete_evaluation()

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

    def test_adjudicate_challenge_emits_domain_event_after_commit(self):
        received_events = []

        def receiver(sender, event, **kwargs):
            received_events.append(event)

        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()
        self.register_complete_evaluation()
        challenge_awarded.connect(
            receiver,
            dispatch_uid="test_adjudicate_challenge_event",
            weak=False,
        )
        try:
            with self.captureOnCommitCallbacks(execute=True):
                decision = adjudicate_challenge(
                    challenge=self.challenge,
                    actor=self.publisher_user,
                    command=AwardDecisionCommand(
                        winning_application_id=self.application.pk,
                        comment="La propuesta ofrece el mejor encaje técnico y operativo.",
                    ),
                )
        finally:
            challenge_awarded.disconnect(
                dispatch_uid="test_adjudicate_challenge_event"
            )

        self.assertEqual(len(received_events), 1)
        event = received_events[0]
        self.assertIsInstance(event, ChallengeAwarded)
        self.assertEqual(event.challenge_id, self.challenge.pk)
        self.assertEqual(event.publisher_organization_id, self.publisher.pk)
        self.assertEqual(event.winning_application_id, self.application.pk)
        self.assertEqual(event.award_decision_id, decision.pk)
        self.assertEqual(event.decided_by_user_id, self.publisher_user.pk)

    def test_adjudicate_challenge_records_timeline_entry_after_commit(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()
        self.register_complete_evaluation()

        with self.captureOnCommitCallbacks(execute=True):
            decision = adjudicate_challenge(
                challenge=self.challenge,
                actor=self.publisher_user,
                command=AwardDecisionCommand(
                    winning_application_id=self.application.pk,
                    comment="La propuesta ofrece el mejor encaje técnico y operativo.",
                ),
            )

        entry = ChallengeTimelineEntry.objects.get(
            challenge=self.challenge,
            event_type=ChallengeTimelineEntry.EventType.CHALLENGE_AWARDED,
        )
        self.assertEqual(entry.actor, self.publisher_user)
        self.assertEqual(entry.award_decision, decision)
        self.assertEqual(
            entry.description,
            "Se registró la adjudicación del desafío.",
        )

    def test_adjudicate_challenge_requires_complete_criterion_evaluations(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()

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
            "La propuesta ganadora debe tener todos sus criterios evaluados antes de adjudicar.",
            captured.exception.messages,
        )

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
        self.register_complete_evaluation()
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

    def test_build_challenge_application_evaluation_summaries_exposes_average_score(self):
        self.challenge.evaluation_criteria = "Capacidad técnica\nExperiencia sectorial"
        self.challenge.save(update_fields=["evaluation_criteria"])
        self.challenge.evaluation_criteria_items.all().delete()
        self.challenge.sync_evaluation_criteria_items()
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save(update_fields=["status"])

        evaluate_application_by_criteria(
            challenge=self.challenge,
            application=self.application,
            actor=self.publisher_user,
            command=EvaluateApplicationCommand(
                application_id=self.application.pk,
                assessments=(
                    CriterionAssessmentInput(
                        criterion_id=self.challenge.evaluation_criteria_items.get(
                            position=1
                        ).pk,
                        score=4,
                        comment="Buen encaje técnico.",
                    ),
                    CriterionAssessmentInput(
                        criterion_id=self.challenge.evaluation_criteria_items.get(
                            position=2
                        ).pk,
                        score=5,
                        comment="Experiencia muy sólida.",
                    ),
                ),
            ),
        )

        summaries = build_challenge_application_evaluation_summaries(self.challenge)

        self.assertEqual(len(summaries), 1)
        summary = summaries[0].evaluation_summary
        self.assertEqual(summary.evaluated_count, 2)
        self.assertEqual(summary.criteria_total, 2)
        self.assertTrue(summary.is_complete)
        self.assertEqual(summary.total_score, 9)
        self.assertEqual(summary.average_score, 4.5)


class EvaluationFlowTests(TestCase):
    def build_complete_evaluation_command(self):
        self.challenge.sync_evaluation_criteria_items()
        return EvaluateApplicationCommand(
            application_id=self.application.pk,
            assessments=tuple(
                CriterionAssessmentInput(
                    criterion_id=criterion.pk,
                    score=4,
                    comment=f"Comentario de evaluación para {criterion.label}.",
                )
                for criterion in self.challenge.evaluation_criteria_items.order_by("position")
            ),
        )

    def build_complete_evaluation_payload(self):
        self.challenge.sync_evaluation_criteria_items()
        payload = {}
        for criterion in self.challenge.evaluation_criteria_items.order_by("position"):
            payload[f"score_{criterion.pk}"] = "4"
            payload[f"comment_{criterion.pk}"] = (
                f"Comentario de evaluación para {criterion.label}."
            )
        return payload

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
            evaluation_criteria="Capacidad técnica y experiencia previa.",
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
        evaluate_application_by_criteria(
            challenge=self.challenge,
            application=self.application,
            actor=self.publisher_user,
            command=self.build_complete_evaluation_command(),
        )
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

    def test_application_evaluation_view_registers_assessments(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()
        self.client.force_login(self.publisher_user)

        response = self.client.post(
            reverse(
                "evaluation:application-criterion-evaluation-update",
                args=[self.challenge.pk, self.application.pk],
            ),
            self.build_complete_evaluation_payload(),
        )

        self.assertRedirects(
            response,
            reverse("marketplace:challenge-detail", args=[self.challenge.pk]),
        )
        self.assertTrue(
            ApplicationCriterionEvaluation.objects.filter(application=self.application).exists()
        )

    def test_challenge_detail_shows_evaluation_history_for_publisher(self):
        self.client.force_login(self.publisher_user)

        with self.captureOnCommitCallbacks(execute=True):
            start_challenge_evaluation(
                challenge=self.challenge,
                actor=self.publisher_user,
            )

        self.challenge.refresh_from_db()
        evaluate_application_by_criteria(
            challenge=self.challenge,
            application=self.application,
            actor=self.publisher_user,
            command=self.build_complete_evaluation_command(),
        )
        with self.captureOnCommitCallbacks(execute=True):
            adjudicate_challenge(
                challenge=self.challenge,
                actor=self.publisher_user,
                command=AwardDecisionCommand(
                    winning_application_id=self.application.pk,
                    comment="Seleccionada por su solidez técnica.",
                ),
            )

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historial de evaluación")
        self.assertContains(response, "Evaluación iniciada")
        self.assertContains(response, "Desafío adjudicado")
        self.assertContains(response, self.publisher_user.username)

    def test_challenge_detail_shows_evaluate_action_for_application_in_under_evaluation(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()
        self.client.force_login(self.publisher_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evaluar propuesta")

    def test_provider_cannot_access_award_decision_view(self):
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save()
        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("evaluation:award-decision-create", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_award_decision_view_shows_application_evaluation_summary(self):
        self.challenge.evaluation_criteria = "Capacidad técnica\nExperiencia sectorial"
        self.challenge.save(update_fields=["evaluation_criteria"])
        self.challenge.evaluation_criteria_items.all().delete()
        self.challenge.sync_evaluation_criteria_items()
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save(update_fields=["status"])
        evaluate_application_by_criteria(
            challenge=self.challenge,
            application=self.application,
            actor=self.publisher_user,
            command=EvaluateApplicationCommand(
                application_id=self.application.pk,
                assessments=(
                    CriterionAssessmentInput(
                        criterion_id=self.challenge.evaluation_criteria_items.get(
                            position=1
                        ).pk,
                        score=4,
                        comment="Buen desempeño técnico.",
                    ),
                    CriterionAssessmentInput(
                        criterion_id=self.challenge.evaluation_criteria_items.get(
                            position=2
                        ).pk,
                        score=5,
                        comment="Amplia experiencia sectorial.",
                    ),
                ),
            ),
        )
        self.client.force_login(self.publisher_user)

        response = self.client.get(
            reverse("evaluation:award-decision-create", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumen comparativo de propuestas")
        self.assertContains(response, "Promedio actual de evaluación")
        self.assertContains(response, "4,50 / 5")
        self.assertContains(
            response,
            "Solo aparecen propuestas con todos los criterios evaluados.",
        )
