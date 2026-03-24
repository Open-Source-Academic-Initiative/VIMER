import shutil
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.corporate.avatar_utils import generate_default_logo
from apps.corporate.models import Organization
from apps.evaluation.application.commands import (
    CriterionAssessmentInput,
    EvaluateApplicationCommand,
)
from apps.evaluation.application.services import evaluate_application_by_criteria
from apps.evaluation.models import ChallengeEvaluationRoleAssignment
from apps.marketplace.application.commands import (
    PublishChallengeCommand,
    SubmitApplicationCommand,
)
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    ChallengePublicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.application.services import (
    publish_challenge,
    submit_challenge_application,
)
from apps.marketplace.models import Application, Challenge


class MediaRootIsolatedTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root = tempfile.mkdtemp()
        cls._override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)
        super().tearDownClass()


class MarketplaceFlowTests(MediaRootIsolatedTestCase):
    def make_application_payload(self):
        return {
            "problem_understanding": "Entendemos el reto y su contexto operativo.",
            "proposed_solution": "Proponemos una solución tecnológica modular.",
            "capabilities_evidence": "Tenemos experiencia, equipo y casos previos relevantes.",
            "execution_plan": "Ejecutaremos en fases con hitos y seguimiento.",
        }

    def setUp(self):
        self.demand_organization = Organization.objects.create(
            tax_id="900000101",
            business_name="Solicitante de prueba",
            chamber_of_commerce_record="CC-101",
            role="DEMAND_SIDE",
            contact_email="solicitante@example.com",
            contact_phone="1111111",
        )
        self.supply_organization = Organization.objects.create(
            tax_id="900000202",
            business_name="Proveedor tecnológico de prueba",
            chamber_of_commerce_record="CC-202",
            role="SUPPLY_SIDE",
            contact_email="proveedor@example.com",
            contact_phone="2222222",
        )
        self.demand_organization.logo = generate_default_logo(
            business_name=self.demand_organization.business_name,
            tax_id=self.demand_organization.tax_id,
        )
        self.demand_organization.save(update_fields=["logo"])
        self.supply_organization.logo = generate_default_logo(
            business_name=self.supply_organization.business_name,
            tax_id=self.supply_organization.tax_id,
        )
        self.supply_organization.save(update_fields=["logo"])
        self.demand_user = get_user_model().objects.create_user(
            username="demand_user",
            email="demand_user@example.com",
            password="ClaveSegura123",
            organization=self.demand_organization,
        )
        self.supply_user = get_user_model().objects.create_user(
            username="supply_user",
            email="supply_user@example.com",
            password="ClaveSegura123",
            organization=self.supply_organization,
        )
        self.challenge = Challenge.objects.create(
            publisher=self.demand_organization,
            title="Existing challenge",
            description="Challenge description",
            application_deadline=timezone.localdate() + timedelta(days=7),
        )

    def test_challenge_create_page_loads_for_demand_side_user(self):
        self.client.force_login(self.demand_user)

        response = self.client.get(reverse("marketplace:challenge-create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "marketplace/challenge_form.html")

    def test_challenge_create_page_forbidden_for_supply_side_user(self):
        self.client.force_login(self.supply_user)

        response = self.client.get(reverse("marketplace:challenge-create"))

        self.assertEqual(response.status_code, 403)

    def test_challenge_list_shows_publisher_logo(self):
        self.client.force_login(self.supply_user)

        response = self.client.get(reverse("marketplace:challenge-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.demand_organization.logo.url)

    def test_challenge_apply_page_includes_challenge_context(self):
        self.client.force_login(self.supply_user)

        response = self.client.get(
            reverse("marketplace:challenge-apply", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["challenge"], self.challenge)

    def test_challenge_apply_page_forbidden_for_demand_side_user(self):
        self.client.force_login(self.demand_user)

        response = self.client.get(
            reverse("marketplace:challenge-apply", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_challenge_detail_hides_apply_action_when_challenge_is_closed(self):
        self.challenge.status = Challenge.Status.CLOSED
        self.challenge.save()
        self.client.force_login(self.supply_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Aplicar al Desafío")
        self.assertContains(
            response,
            "Este desafío no está abierto para recibir propuestas.",
        )

    def test_challenge_apply_duplicate_submission_shows_duplicate_message(self):
        Application.objects.create(
            challenge=self.challenge,
            applicant=self.supply_organization,
            proposal_text="Initial proposal",
            problem_understanding="Entendimiento inicial",
            proposed_solution="Solución inicial",
            capabilities_evidence="Capacidades iniciales",
            execution_plan="Plan inicial",
        )
        self.client.force_login(self.supply_user)

        response = self.client.post(
            reverse("marketplace:challenge-apply", args=[self.challenge.pk]),
            self.make_application_payload(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            None,
            "Tu organización ya envió una propuesta para este desafío.",
        )

    def test_challenge_apply_closed_challenge_shows_not_open_message(self):
        self.challenge.status = Challenge.Status.CLOSED
        self.challenge.save()
        self.client.force_login(self.supply_user)

        response = self.client.post(
            reverse("marketplace:challenge-apply", args=[self.challenge.pk]),
            self.make_application_payload(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            None,
            "Este desafío no está abierto para recibir propuestas.",
        )

    def test_challenge_detail_shows_applicant_logo_for_publisher(self):
        Application.objects.create(
            challenge=self.challenge,
            applicant=self.supply_organization,
            proposal_text="Initial proposal",
            problem_understanding="Entendimiento inicial",
            proposed_solution="Solución inicial",
            capabilities_evidence="Capacidades iniciales",
            execution_plan="Plan inicial",
        )
        self.client.force_login(self.demand_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.supply_organization.logo.url)

    def test_challenge_detail_shows_evaluation_criteria(self):
        self.challenge.evaluation_criteria = (
            "Experiencia sectorial\n"
            "Viabilidad técnica\n"
            "Plan de ejecución"
        )
        self.challenge.save()
        self.challenge.evaluation_criteria_items.create(label="Experiencia sectorial", position=1)
        self.challenge.evaluation_criteria_items.create(label="Viabilidad técnica", position=2)
        self.challenge.evaluation_criteria_items.create(label="Plan de ejecución", position=3)
        self.client.force_login(self.supply_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Criterios de evaluación")
        self.assertContains(response, "Experiencia sectorial")
        self.assertContains(response, "Viabilidad técnica")
        self.assertContains(response, "Plan de ejecución")

    def test_challenge_detail_shows_application_average_score_for_publisher(self):
        self.challenge.evaluation_criteria = "Capacidad técnica\nExperiencia sectorial"
        self.challenge.save(update_fields=["evaluation_criteria"])
        self.challenge.evaluation_criteria_items.all().delete()
        self.challenge.sync_evaluation_criteria_items()
        application = Application.objects.create(
            challenge=self.challenge,
            applicant=self.supply_organization,
            proposal_text="Initial proposal",
            problem_understanding="Entendimiento inicial",
            proposed_solution="Solución inicial",
            capabilities_evidence="Capacidades iniciales",
            execution_plan="Plan inicial",
        )
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save(update_fields=["status"])
        ChallengeEvaluationRoleAssignment.objects.create(
            challenge=self.challenge,
            user=self.demand_user,
            role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR,
        )
        criteria = list(self.challenge.evaluation_criteria_items.order_by("position"))
        evaluate_application_by_criteria(
            challenge=self.challenge,
            application=application,
            actor=self.demand_user,
            command=EvaluateApplicationCommand(
                application_id=application.pk,
                assessments=(
                    CriterionAssessmentInput(
                        criterion_id=criteria[0].pk,
                        score=4,
                        comment="Buen encaje técnico.",
                    ),
                    CriterionAssessmentInput(
                        criterion_id=criteria[1].pk,
                        score=5,
                        comment="Experiencia sólida.",
                    ),
                ),
            ),
        )
        self.client.force_login(self.demand_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Promedio actual")
        self.assertContains(response, "4,50 / 5")
        self.assertContains(response, "Detalle por criterio")
        self.assertContains(response, "Posición comparativa actual")
        self.assertContains(response, "Ranking elegible para adjudicación")

    def test_challenge_create_persists_evaluation_criteria(self):
        self.client.force_login(self.demand_user)

        response = self.client.post(
            reverse("marketplace:challenge-create"),
            {
                "title": "Nuevo desafío con criterios",
                "description": "Descripción con criterios explícitos.",
                "evaluation_criteria": (
                    "Alineación técnica\n"
                    "Capacidad de ejecución\n"
                    "Costo total"
                ),
                "application_deadline": timezone.localdate() + timedelta(days=14),
            },
        )

        self.assertRedirects(response, reverse("marketplace:challenge-list"))
        created_challenge = Challenge.objects.get(title="Nuevo desafío con criterios")
        self.assertEqual(
            created_challenge.evaluation_criteria,
            "Alineación técnica\nCapacidad de ejecución\nCosto total",
        )
        self.assertEqual(
            list(created_challenge.evaluation_criteria_items.values_list("label", flat=True)),
            ["Alineación técnica", "Capacidad de ejecución", "Costo total"],
        )

    def test_challenge_apply_requires_all_proposal_components(self):
        self.client.force_login(self.supply_user)
        payload = self.make_application_payload()
        payload["execution_plan"] = ""

        response = self.client.post(
            reverse("marketplace:challenge-apply", args=[self.challenge.pk]),
            payload,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors.get("execution_plan"))


class MarketplaceApplicationServiceTests(MediaRootIsolatedTestCase):
    def setUp(self):
        self.demand_organization = Organization.objects.create(
            tax_id="903000001",
            business_name="Organización solicitante",
            chamber_of_commerce_record="CC-301",
            role="DEMAND_SIDE",
            contact_email="solicitante-app@example.com",
            contact_phone="1111111",
        )
        self.supply_organization = Organization.objects.create(
            tax_id="903000002",
            business_name="Proveedor tecnológico",
            chamber_of_commerce_record="CC-302",
            role="SUPPLY_SIDE",
            contact_email="proveedor-app@example.com",
            contact_phone="2222222",
        )
        self.challenge = Challenge.objects.create(
            publisher=self.demand_organization,
            title="Challenge",
            description="Description",
            application_deadline=timezone.localdate() + timedelta(days=7),
        )

    def test_publish_challenge_sets_published_status_and_deadline(self):
        future_deadline = timezone.localdate() + timedelta(days=10)

        challenge = publish_challenge(
            publisher=self.demand_organization,
            command=PublishChallengeCommand(
                title="Published challenge",
                description="Description",
                evaluation_criteria="Viabilidad técnica\nExperiencia\nCosto",
                application_deadline=future_deadline,
            ),
        )

        self.assertEqual(challenge.status, Challenge.Status.PUBLISHED)
        self.assertEqual(challenge.application_deadline, future_deadline)
        self.assertEqual(
            challenge.evaluation_criteria,
            "Viabilidad técnica\nExperiencia\nCosto",
        )
        self.assertEqual(
            list(challenge.evaluation_criteria_items.values_list("label", flat=True)),
            ["Viabilidad técnica", "Experiencia", "Costo"],
        )

    def test_publish_challenge_rejects_invalid_publisher_role_with_validation_error(self):
        with self.assertRaises(ChallengePublicationValidationError) as captured:
            publish_challenge(
                publisher=self.supply_organization,
                command=PublishChallengeCommand(
                    title="Invalid challenge",
                    description="Description",
                    evaluation_criteria="Criterios",
                ),
            )

        self.assertIn(
            "Solo las organizaciones con rol Solicitante pueden publicar desafíos.",
            captured.exception.messages,
        )

    def test_publish_challenge_rejects_past_deadline_for_published_challenge(self):
        with self.assertRaises(ChallengePublicationValidationError) as captured:
            publish_challenge(
                publisher=self.demand_organization,
                command=PublishChallengeCommand(
                    title="Invalid challenge",
                    description="Description",
                    evaluation_criteria="Criterios",
                    application_deadline=timezone.localdate() - timedelta(days=1),
                ),
            )

        self.assertIn(
            "La fecha límite de aplicación no puede estar en el pasado para un desafío publicado.",
            captured.exception.messages,
        )

    def test_submit_application_rejects_duplicates(self):
        command = SubmitApplicationCommand(
            problem_understanding="Entendimiento inicial",
            proposed_solution="Solución inicial",
            capabilities_evidence="Capacidades iniciales",
            execution_plan="Plan inicial",
        )

        submit_challenge_application(
            challenge=self.challenge,
            applicant=self.supply_organization,
            command=command,
        )

        with self.assertRaises(DuplicateChallengeApplicationError):
            submit_challenge_application(
                challenge=self.challenge,
                applicant=self.supply_organization,
                command=command,
            )

    def test_submit_application_rejects_invalid_applicant_role_with_validation_error(self):
        command = SubmitApplicationCommand(
            problem_understanding="Entendimiento",
            proposed_solution="Solución",
            capabilities_evidence="Capacidades",
            execution_plan="Plan",
        )

        with self.assertRaises(ChallengeApplicationValidationError) as captured:
            submit_challenge_application(
                challenge=self.challenge,
                applicant=self.demand_organization,
                command=command,
            )

        self.assertIn(
            "Solo las organizaciones con rol Proveedor tecnológico pueden aplicar a desafíos.",
            captured.exception.messages,
        )

    def test_submit_application_rejects_closed_challenge(self):
        self.challenge.status = Challenge.Status.CLOSED
        self.challenge.save()

        with self.assertRaises(ChallengeApplicationValidationError) as captured:
            submit_challenge_application(
                challenge=self.challenge,
                applicant=self.supply_organization,
                command=SubmitApplicationCommand(
                    problem_understanding="Entendimiento",
                    proposed_solution="Solución",
                    capabilities_evidence="Capacidades",
                    execution_plan="Plan",
                ),
            )

        self.assertIn(
            "Este desafío no está abierto para recibir propuestas.",
            captured.exception.messages,
        )

    def test_submit_application_rejects_expired_challenge(self):
        with patch("apps.marketplace.models.timezone.localdate") as mocked_localdate:
            mocked_localdate.return_value = self.challenge.application_deadline + timedelta(days=1)

            with self.assertRaises(ChallengeApplicationValidationError) as captured:
                submit_challenge_application(
                    challenge=self.challenge,
                    applicant=self.supply_organization,
                    command=SubmitApplicationCommand(
                        problem_understanding="Entendimiento",
                        proposed_solution="Solución",
                        capabilities_evidence="Capacidades",
                        execution_plan="Plan",
                    ),
                )

        self.assertIn(
            "Este desafío no está abierto para recibir propuestas.",
            captured.exception.messages,
        )

    def test_submit_application_requires_all_structured_components(self):
        with self.assertRaises(ChallengeApplicationValidationError) as captured:
            submit_challenge_application(
                challenge=self.challenge,
                applicant=self.supply_organization,
                command=SubmitApplicationCommand(
                    problem_understanding="",
                    proposed_solution="Solución",
                    capabilities_evidence="Capacidades",
                    execution_plan="Plan",
                ),
            )

        self.assertIn(
            "La propuesta debe incluir: entendimiento del problema.",
            captured.exception.messages,
        )

    def test_submitted_application_is_immutable(self):
        application = submit_challenge_application(
            challenge=self.challenge,
            applicant=self.supply_organization,
            command=SubmitApplicationCommand(
                problem_understanding="Entendimiento",
                proposed_solution="Solución",
                capabilities_evidence="Capacidades",
                execution_plan="Plan",
            ),
        )

        application.execution_plan = "Plan modificado"

        with self.assertRaisesMessage(
            ValidationError,
            "Una propuesta enviada no puede modificarse después del envío.",
        ):
            application.save()
