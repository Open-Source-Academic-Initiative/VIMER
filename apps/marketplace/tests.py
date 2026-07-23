import shutil
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.corporate.avatar_utils import generate_default_logo
from apps.corporate.models import Organization
from apps.evaluation.application.commands import (
    AwardDecisionCommand,
    CriterionAssessmentInput,
    EvaluateApplicationCommand,
)
from apps.evaluation.application.services import (
    adjudicate_challenge,
    evaluate_application_by_criteria,
)
from apps.evaluation.models import ChallengeEvaluationRoleAssignment
from apps.marketplace.application.applications import (
    save_application_draft,
    submit_challenge_application,
)
from apps.marketplace.application.challenges import publish_challenge
from apps.marketplace.application.commands import (
    PublishChallengeCommand,
    SaveApplicationDraftCommand,
    SubmitApplicationCommand,
)
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    ChallengePublicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.content import render_markdown
from apps.marketplace.models import (
    Application,
    ApplicationAttachment,
    Challenge,
    ChallengeAttachment,
    ChallengeCategory,
)


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


class MarketplaceSharedFixtureMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.demand_organization = Organization.objects.create(
            tax_id="900000101",
            business_name="Solicitante de prueba",
            chamber_of_commerce_record="CC-101",
            role="DEMAND_SIDE",
            contact_email="solicitante@example.com",
            contact_phone="1111111",
        )
        cls.supply_organization = Organization.objects.create(
            tax_id="900000202",
            business_name="Proveedor tecnológico de prueba",
            chamber_of_commerce_record="CC-202",
            role="SUPPLY_SIDE",
            contact_email="proveedor@example.com",
            contact_phone="2222222",
        )
        cls.demand_organization.logo = generate_default_logo(
            business_name=cls.demand_organization.business_name,
            tax_id=cls.demand_organization.tax_id,
        )
        cls.demand_organization.save(update_fields=["logo"])
        cls.supply_organization.logo = generate_default_logo(
            business_name=cls.supply_organization.business_name,
            tax_id=cls.supply_organization.tax_id,
        )
        cls.supply_organization.save(update_fields=["logo"])
        User = get_user_model()
        cls.demand_user = User.objects.create_user(
            username="demand_user",
            email="demand_user@example.com",
            password="ClaveSegura123",
            organization=cls.demand_organization,
            is_email_verified=True,
        )
        cls.supply_user = User.objects.create_user(
            username="supply_user",
            email="supply_user@example.com",
            password="ClaveSegura123",
            organization=cls.supply_organization,
            is_email_verified=True,
        )
        cls.challenge = Challenge.objects.create(
            publisher=cls.demand_organization,
            title="Existing challenge",
            description="Challenge description",
            status=Challenge.Status.PUBLISHED,
            application_deadline=timezone.localdate() + timedelta(days=7),
        )
        cls.category = ChallengeCategory.objects.first()

    def setUp(self):
        super().setUp()
        self.demand_organization = Organization.objects.get(
            pk=self.demand_organization.pk
        )
        self.supply_organization = Organization.objects.get(
            pk=self.supply_organization.pk
        )
        User = get_user_model()
        self.demand_user = User.objects.get(pk=self.demand_user.pk)
        self.supply_user = User.objects.get(pk=self.supply_user.pk)
        self.challenge = Challenge.objects.get(pk=self.challenge.pk)
        self.category = ChallengeCategory.objects.get(pk=self.category.pk)

    def make_application_payload(self):
        return {
            "problem_understanding": "Entendemos el reto y su contexto operativo.",
            "proposed_solution": "Proponemos una solución tecnológica modular.",
            "capabilities_evidence": (
                "Tenemos experiencia, equipo y casos previos relevantes."
            ),
            "execution_plan": "Ejecutaremos en fases con hitos y seguimiento.",
            "confirm_submission": "on",
        }

    def create_submitted_application(self):
        return Application.objects.create(
            challenge=self.challenge,
            applicant=self.supply_organization,
            status=Application.Status.SUBMITTED,
            proposal_text="Initial proposal",
            problem_understanding="Entendimiento inicial",
            proposed_solution="Solución inicial",
            capabilities_evidence="Capacidades iniciales",
            execution_plan="Plan inicial",
        )

    def create_draft_application(self):
        return Application.objects.create(
            challenge=self.challenge,
            applicant=self.supply_organization,
            status=Application.Status.DRAFT,
            problem_understanding="Entendimiento borrador",
            proposed_solution="",
            capabilities_evidence="Capacidades borrador",
            execution_plan="",
        )


class DesafioFlowTests(MarketplaceSharedFixtureMixin, MediaRootIsolatedTestCase):
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

    def test_challenge_list_hides_draft_challenges_from_non_publishers(self):
        draft_challenge = Challenge.objects.create(
            publisher=self.demand_organization,
            title="Borrador interno",
            description="No debe verse fuera de la organización publicadora.",
            status=Challenge.Status.DRAFT,
        )
        self.client.force_login(self.supply_user)

        response = self.client.get(reverse("marketplace:challenge-list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, draft_challenge.title)

    def test_challenge_list_shows_publisher_own_draft_challenges(self):
        draft_challenge = Challenge.objects.create(
            publisher=self.demand_organization,
            title="Borrador visible para publisher",
            description="Debe verse para su organización publicadora.",
            status=Challenge.Status.DRAFT,
        )
        self.client.force_login(self.demand_user)

        response = self.client.get(reverse("marketplace:challenge-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, draft_challenge.title)

    def test_challenge_detail_hides_draft_challenge_from_non_publisher(self):
        self.challenge.status = Challenge.Status.DRAFT
        self.challenge.save(update_fields=["status"])
        self.client.force_login(self.supply_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_challenge_detail_shows_draft_challenge_to_publisher(self):
        self.challenge.status = Challenge.Status.DRAFT
        self.challenge.save(update_fields=["status"])
        self.client.force_login(self.demand_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.challenge.title)

    def test_challenge_detail_shows_evaluation_criteria(self):
        self.challenge.evaluation_criteria = (
            "Experiencia sectorial\n"
            "Viabilidad técnica\n"
            "Plan de ejecución"
        )
        self.challenge.save()
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
        application = self.create_submitted_application()
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
        self.assertContains(response, "Posición competitiva actual")

    def test_challenge_detail_hides_applicant_identity_for_publisher_before_award(self):
        self.create_submitted_application()
        self.client.force_login(self.demand_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Su contenido permanece sellado")
        self.assertEqual(response.context["submitted_application_count"], 1)
        self.assertEqual(response.context["challenge_applications"], [])
        self.assertNotContains(response, self.supply_organization.business_name)

    def test_challenge_detail_hides_evaluation_read_models_from_non_publisher(self):
        self.challenge.evaluation_criteria = "Capacidad técnica\nExperiencia sectorial"
        self.challenge.save(update_fields=["evaluation_criteria"])
        self.challenge.evaluation_criteria_items.all().delete()
        self.challenge.sync_evaluation_criteria_items()
        application = self.create_submitted_application()
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save(update_fields=["status"])
        ChallengeEvaluationRoleAssignment.objects.create(
            challenge=self.challenge,
            user=self.demand_user,
            role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR,
        )
        evaluate_application_by_criteria(
            challenge=self.challenge,
            application=application,
            actor=self.demand_user,
            command=EvaluateApplicationCommand(
                application_id=application.pk,
                assessments=tuple(
                    CriterionAssessmentInput(
                        criterion_id=criterion.pk,
                        score=4,
                        comment=f"Evaluación para {criterion.label}.",
                    )
                    for criterion in self.challenge.evaluation_criteria_items.order_by(
                        "position"
                    )
                ),
            ),
        )
        self.client.force_login(self.supply_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Promedio actual")
        self.assertNotContains(response, "Posición competitiva actual")
        self.assertNotContains(response, "Detalle por criterio")
        self.assertEqual(response.context["challenge_applications"], [])
        self.assertEqual(list(response.context["timeline_entries"]), [])
        self.assertIsNone(response.context["award_decision"])

    def test_challenge_detail_shows_applicant_logo_for_publisher_after_award(self):
        self.challenge.evaluation_criteria = "Capacidad técnica"
        self.challenge.save(update_fields=["evaluation_criteria"])
        self.challenge.evaluation_criteria_items.all().delete()
        self.challenge.sync_evaluation_criteria_items()
        application = self.create_submitted_application()
        self.challenge.status = Challenge.Status.UNDER_EVALUATION
        self.challenge.save(update_fields=["status"])
        ChallengeEvaluationRoleAssignment.objects.create(
            challenge=self.challenge,
            user=self.demand_user,
            role=ChallengeEvaluationRoleAssignment.Role.EVALUATOR,
        )
        ChallengeEvaluationRoleAssignment.objects.create(
            challenge=self.challenge,
            user=self.demand_user,
            role=ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR,
        )
        criterion = self.challenge.evaluation_criteria_items.get(position=1)
        evaluate_application_by_criteria(
            challenge=self.challenge,
            application=application,
            actor=self.demand_user,
            command=EvaluateApplicationCommand(
                application_id=application.pk,
                assessments=(
                    CriterionAssessmentInput(
                        criterion_id=criterion.pk,
                        score=4,
                        comment="Buen encaje técnico.",
                    ),
                ),
            ),
        )
        adjudicate_challenge(
            challenge=self.challenge,
            actor=self.demand_user,
            command=AwardDecisionCommand(
                winning_application_id=application.pk,
                comment="Seleccionada para adjudicación.",
            ),
        )
        self.client.force_login(self.demand_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.supply_organization.logo.url)


class PropuestaFlowTests(MarketplaceSharedFixtureMixin, MediaRootIsolatedTestCase):
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
        self.assertNotContains(response, "Presentar propuesta")
        self.assertContains(
            response,
            "Este desafío no está abierto para guardar o enviar propuestas.",
        )

    def test_challenge_apply_duplicate_submission_shows_duplicate_message(self):
        self.create_submitted_application()
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

    def test_challenge_detail_shows_continue_draft_action_for_existing_draft(self):
        self.create_draft_application()
        self.client.force_login(self.supply_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continuar borrador")
        self.assertContains(response, "Tienes un borrador privado guardado")

    def test_challenge_apply_page_reopens_existing_draft(self):
        draft = self.create_draft_application()
        self.client.force_login(self.supply_user)

        response = self.client.get(
            reverse("marketplace:challenge-apply", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["existing_application"].pk, draft.pk)
        self.assertContains(response, "Guardar borrador")
        self.assertContains(response, draft.problem_understanding)

    def test_challenge_apply_draft_save_accepts_incomplete_payload(self):
        self.client.force_login(self.supply_user)
        payload = {
            "problem_understanding": "Borrador inicial",
            "proposed_solution": "",
            "capabilities_evidence": "",
            "execution_plan": "",
            "intent": "draft",
        }

        response = self.client.post(
            reverse("marketplace:challenge-apply", args=[self.challenge.pk]),
            payload,
        )

        self.assertRedirects(
            response,
            reverse("marketplace:challenge-apply", args=[self.challenge.pk]),
        )
        application = Application.objects.get(
            challenge=self.challenge,
            applicant=self.supply_organization,
        )
        self.assertEqual(application.status, Application.Status.DRAFT)
        self.assertEqual(application.problem_understanding, "Borrador inicial")
        self.assertIsNone(application.applied_at)

    def test_challenge_apply_submit_reuses_existing_draft(self):
        draft = self.create_draft_application()
        self.client.force_login(self.supply_user)
        payload = self.make_application_payload() | {"intent": "submit"}

        response = self.client.post(
            reverse("marketplace:challenge-apply", args=[self.challenge.pk]),
            payload,
        )

        self.assertRedirects(
            response,
            reverse("marketplace:challenge-detail", args=[self.challenge.pk]),
        )
        draft.refresh_from_db()
        self.assertEqual(draft.status, Application.Status.SUBMITTED)
        self.assertIsNotNone(draft.applied_at)
        self.assertEqual(Application.objects.count(), 1)

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
            "Este desafío no está abierto para guardar o enviar propuestas.",
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

    def test_publisher_detail_hides_private_draft_applications(self):
        self.create_draft_application()
        self.client.force_login(self.demand_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["challenge_applications"], [])
        self.assertContains(response, "Aún no hay propuestas para este desafío.")


class DesafioServiceTests(MarketplaceSharedFixtureMixin, MediaRootIsolatedTestCase):
    def test_publish_challenge_sets_published_status_and_deadline(self):
        future_deadline = timezone.localdate() + timedelta(days=10)

        challenge = publish_challenge(
            publisher=self.demand_organization,
            command=PublishChallengeCommand(
                title="Published challenge",
                description="Description",
                evaluation_criteria="Viabilidad técnica\nExperiencia\nCosto",
                application_deadline=future_deadline,
                budget_amount="150000000.00",
                budget_currency=Challenge.Currency.COP,
                category_ids=(self.category.pk,),
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
                    category_ids=(self.category.pk,),
                ),
            )

        self.assertIn(
            "La fecha límite de aplicación no puede estar en el pasado para un desafío publicado.",
            captured.exception.messages,
        )

    def test_publish_challenge_rejects_missing_categories(self):
        with self.assertRaises(ChallengePublicationValidationError) as captured:
            publish_challenge(
                publisher=self.demand_organization,
                command=PublishChallengeCommand(
                    title="Challenge without categories",
                    description="Description",
                    evaluation_criteria="Criterios",
                ),
            )

        self.assertIn(
            "Debes seleccionar al menos una categoría para el desafío.",
            captured.exception.messages,
        )
        self.assertFalse(
            Challenge.objects.filter(title="Challenge without categories").exists()
        )

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
                "budget_amount": "250000000.00",
                "budget_currency": Challenge.Currency.COP,
                "categories": [self.category.pk],
            },
        )

        self.assertRedirects(response, reverse("marketplace:challenge-list"))
        created_challenge = Challenge.objects.get(title="Nuevo desafío con criterios")
        self.assertEqual(
            created_challenge.evaluation_criteria,
            "Alineación técnica\nCapacidad de ejecución\nCosto total",
        )
        self.assertEqual(
            list(
                created_challenge.evaluation_criteria_items.values_list(
                    "label",
                    flat=True,
                )
            ),
            ["Alineación técnica", "Capacidad de ejecución", "Costo total"],
        )

    def test_challenge_syncs_structured_criteria_when_text_changes(self):
        self.challenge.evaluation_criteria = "Criterio A\nCriterio B"
        self.challenge.save(update_fields=["evaluation_criteria"])
        self.assertEqual(
            list(
                self.challenge.evaluation_criteria_items.order_by("position").values_list(
                    "label",
                    flat=True,
                )
            ),
            ["Criterio A", "Criterio B"],
        )

        self.challenge.evaluation_criteria = "Criterio A actualizado\nCriterio C"
        self.challenge.save(update_fields=["evaluation_criteria"])

        self.assertEqual(
            list(
                self.challenge.evaluation_criteria_items.order_by("position").values_list(
                    "label",
                    flat=True,
                )
            ),
            ["Criterio A actualizado", "Criterio C"],
        )


class PropuestaServiceTests(MarketplaceSharedFixtureMixin, MediaRootIsolatedTestCase):
    def test_save_application_draft_allows_incomplete_components(self):
        draft = save_application_draft(
            challenge=self.challenge,
            applicant=self.supply_organization,
            command=SaveApplicationDraftCommand(
                problem_understanding="Borrador",
                proposed_solution="",
                capabilities_evidence="",
                execution_plan="",
            ),
        )

        self.assertEqual(draft.status, Application.Status.DRAFT)
        self.assertEqual(draft.problem_understanding, "Borrador")
        self.assertIsNone(draft.applied_at)

    def test_submit_application_promotes_existing_draft(self):
        draft = save_application_draft(
            challenge=self.challenge,
            applicant=self.supply_organization,
            command=SaveApplicationDraftCommand(
                problem_understanding="Borrador",
                proposed_solution="",
                capabilities_evidence="",
                execution_plan="",
            ),
        )

        submitted = submit_challenge_application(
            challenge=self.challenge,
            applicant=self.supply_organization,
            command=SubmitApplicationCommand(
                problem_understanding="Entendimiento",
                proposed_solution="Solución",
                capabilities_evidence="Capacidades",
                execution_plan="Plan",
            ),
        )

        self.assertEqual(submitted.pk, draft.pk)
        self.assertEqual(submitted.status, Application.Status.SUBMITTED)
        self.assertIsNotNone(submitted.applied_at)

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
            "Este desafío no está abierto para guardar o enviar propuestas.",
            captured.exception.messages,
        )

    def test_submit_application_rejects_expired_challenge(self):
        with patch("apps.marketplace.models.timezone.localdate") as mocked_localdate:
            mocked_localdate.return_value = (
                self.challenge.application_deadline + timedelta(days=1)
            )

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
            "Este desafío no está abierto para guardar o enviar propuestas.",
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


class MarkdownSanitizationTests(TestCase):
    def test_render_markdown_keeps_safe_formatting(self):
        html = render_markdown("**Solución** con [enlace](https://vimer.example.org)")

        self.assertIn("<strong>Solución</strong>", html)
        self.assertIn('href="https://vimer.example.org"', html)

    def test_render_markdown_strips_script_tags(self):
        html = render_markdown("Texto<script>alert('xss')</script>")

        self.assertNotIn("<script>", html)
        self.assertNotIn("</script>", html)

    def test_render_markdown_drops_unsafe_link_protocols(self):
        html = render_markdown("[click](javascript:alert(1))")

        self.assertNotIn("javascript:", html)

    def test_challenge_rendered_description_is_sanitized(self):
        challenge = Challenge.objects.create(
            publisher=self.demand_organization
            if hasattr(self, "demand_organization")
            else Organization.objects.create(
                tax_id="900000909",
                business_name="Markdown Org",
                chamber_of_commerce_record="CC-MD",
                role="DEMAND_SIDE",
                contact_email="md@example.com",
                contact_phone="3000000000",
            ),
            title="Reto markdown",
            description="**Importante**<script>alert(1)</script>",
        )

        rendered = challenge.rendered_description

        self.assertIn("<strong>Importante</strong>", rendered)
        self.assertNotIn("<script>", rendered)


class ChallengeSearchAndFilterTests(
    MarketplaceSharedFixtureMixin, MediaRootIsolatedTestCase
):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_category = ChallengeCategory.objects.create(
            name="Categoría de búsqueda",
            slug="categoria-busqueda",
            position=99,
        )
        cls.robotics_challenge = Challenge.objects.create(
            publisher=cls.demand_organization,
            title="Robótica industrial",
            description="Automatización de planta",
            status=Challenge.Status.PUBLISHED,
        )
        cls.robotics_challenge.categories.add(cls.search_category)
        cls.solar_challenge = Challenge.objects.create(
            publisher=cls.demand_organization,
            title="Energía solar",
            description="Optimización de paneles",
            status=Challenge.Status.PUBLISHED,
        )
        cls.closed_challenge = Challenge.objects.create(
            publisher=cls.demand_organization,
            title="Reto cerrado",
            description="Ya no admite propuestas",
            status=Challenge.Status.CLOSED,
        )

    def test_search_filters_by_title(self):
        self.client.force_login(self.demand_user)

        response = self.client.get(reverse("marketplace:challenge-list"), {"q": "Robótica"})

        self.assertContains(response, "Robótica industrial")
        self.assertNotContains(response, "Energía solar")

    def test_filter_by_category(self):
        self.client.force_login(self.demand_user)

        response = self.client.get(
            reverse("marketplace:challenge-list"),
            {"category": self.search_category.slug},
        )

        self.assertContains(response, "Robótica industrial")
        self.assertNotContains(response, "Energía solar")

    def test_filter_by_status(self):
        self.client.force_login(self.demand_user)

        response = self.client.get(
            reverse("marketplace:challenge-list"),
            {"status": Challenge.Status.CLOSED},
        )

        self.assertContains(response, "Reto cerrado")
        self.assertNotContains(response, "Robótica industrial")


class AttachmentDownloadPermissionTests(
    MarketplaceSharedFixtureMixin, MediaRootIsolatedTestCase
):
    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.outsider_organization = Organization.objects.create(
            tax_id="900000303",
            business_name="Organización ajena",
            chamber_of_commerce_record="CC-303",
            role="SUPPLY_SIDE",
            contact_email="ajena@example.com",
            contact_phone="3333333",
        )
        self.outsider_user = User.objects.create_user(
            username="outsider_user",
            email="outsider@example.com",
            password="ClaveSegura123",
            organization=self.outsider_organization,
            is_email_verified=True,
        )

    def _make_pdf(self, name="documento.pdf"):
        return SimpleUploadedFile(
            name, b"%PDF-1.4 contenido de prueba", content_type="application/pdf"
        )

    def _create_application_attachment(self):
        application = self.create_submitted_application()
        attachment = ApplicationAttachment(
            application=application,
            uploaded_by=self.supply_user,
            file=self._make_pdf("propuesta.pdf"),
        )
        attachment.save()
        return attachment

    def test_applicant_can_download_application_attachment(self):
        attachment = self._create_application_attachment()
        self.client.force_login(self.supply_user)

        response = self.client.get(
            reverse(
                "marketplace:application-attachment-download",
                args=[attachment.opaque_id],
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_publisher_cannot_download_application_attachment_before_award(self):
        attachment = self._create_application_attachment()
        self.client.force_login(self.demand_user)

        response = self.client.get(
            reverse(
                "marketplace:application-attachment-download",
                args=[attachment.opaque_id],
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_unrelated_organization_cannot_download_application_attachment(self):
        attachment = self._create_application_attachment()
        self.client.force_login(self.outsider_user)

        response = self.client.get(
            reverse(
                "marketplace:application-attachment-download",
                args=[attachment.opaque_id],
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        attachment = self._create_application_attachment()

        response = self.client.get(
            reverse(
                "marketplace:application-attachment-download",
                args=[attachment.opaque_id],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_draft_challenge_attachment_is_private_to_publisher(self):
        draft_challenge = Challenge.objects.create(
            publisher=self.demand_organization,
            title="Desafío en borrador",
            description="Aún no publicado",
            status=Challenge.Status.DRAFT,
        )
        attachment = ChallengeAttachment(
            challenge=draft_challenge,
            uploaded_by=self.demand_user,
            file=self._make_pdf("anexo.pdf"),
        )
        attachment.save()
        download_url = reverse(
            "marketplace:challenge-attachment-download", args=[attachment.opaque_id]
        )

        self.client.force_login(self.outsider_user)
        forbidden_response = self.client.get(download_url)
        self.assertEqual(forbidden_response.status_code, 403)

        self.client.force_login(self.demand_user)
        allowed_response = self.client.get(download_url)
        self.assertEqual(allowed_response.status_code, 200)


class DraftAttachmentManagementTests(
    MarketplaceSharedFixtureMixin, MediaRootIsolatedTestCase
):
    def _make_pdf(self, name="documento.pdf"):
        return SimpleUploadedFile(
            name, b"%PDF-1.4 contenido de prueba", content_type="application/pdf"
        )

    def _make_fake_pdf(self, name="falso.pdf"):
        return SimpleUploadedFile(
            name, b"MZ ejecutable disfrazado", content_type="application/pdf"
        )

    def _save_draft_with_attachments(self, attachments):
        return save_application_draft(
            challenge=self.challenge,
            applicant=self.supply_organization,
            command=SaveApplicationDraftCommand(
                problem_understanding="Borrador",
                attachments=tuple(attachments),
            ),
            actor=self.supply_user,
        )

    def test_attachment_count_limit_is_cumulative_across_draft_saves(self):
        max_count = settings.MARKETPLACE_ATTACHMENT_MAX_COUNT
        self._save_draft_with_attachments(
            [self._make_pdf(f"adjunto-{index}.pdf") for index in range(max_count)]
        )

        with self.assertRaises(ChallengeApplicationValidationError) as captured:
            self._save_draft_with_attachments([self._make_pdf("uno-mas.pdf")])

        self.assertIn(str(max_count), captured.exception.messages[0])
        application = Application.objects.get(
            challenge=self.challenge, applicant=self.supply_organization
        )
        self.assertEqual(application.attachments.count(), max_count)

    def test_attachment_with_spoofed_content_type_is_rejected(self):
        with self.assertRaises(ChallengeApplicationValidationError) as captured:
            self._save_draft_with_attachments([self._make_fake_pdf()])

        self.assertIn(
            "Solo se permiten archivos PDF, JPG o PNG.",
            captured.exception.messages,
        )

    def test_owner_can_delete_attachment_from_draft(self):
        draft = self._save_draft_with_attachments([self._make_pdf()])
        attachment = draft.attachments.first()
        self.client.force_login(self.supply_user)

        response = self.client.post(
            reverse(
                "marketplace:application-attachment-delete",
                args=[attachment.opaque_id],
            ),
            {"confirm": "on"},
        )

        self.assertRedirects(
            response,
            reverse("marketplace:challenge-apply", args=[self.challenge.pk]),
        )
        self.assertFalse(
            ApplicationAttachment.objects.filter(pk=attachment.pk).exists()
        )

    def test_other_organization_cannot_delete_draft_attachment(self):
        draft = self._save_draft_with_attachments([self._make_pdf()])
        attachment = draft.attachments.first()
        User = get_user_model()
        outsider_organization = Organization.objects.create(
            tax_id="900000404",
            business_name="Proveedor ajeno",
            chamber_of_commerce_record="CC-404",
            role="SUPPLY_SIDE",
            contact_email="ajeno@example.com",
            contact_phone="4444444",
        )
        outsider_user = User.objects.create_user(
            username="outsider_deleter",
            email="outsider_deleter@example.com",
            password="ClaveSegura123",
            organization=outsider_organization,
            is_email_verified=True,
        )
        self.client.force_login(outsider_user)

        self.client.post(
            reverse(
                "marketplace:application-attachment-delete",
                args=[attachment.opaque_id],
            ),
            {"confirm": "on"},
        )

        self.assertTrue(
            ApplicationAttachment.objects.filter(pk=attachment.pk).exists()
        )

    def test_submitted_application_attachment_cannot_be_deleted(self):
        application = self.create_submitted_application()
        attachment = ApplicationAttachment(
            application=application,
            uploaded_by=self.supply_user,
            file=self._make_pdf("propuesta-final.pdf"),
        )
        attachment.save()
        self.client.force_login(self.supply_user)

        self.client.post(
            reverse(
                "marketplace:application-attachment-delete",
                args=[attachment.opaque_id],
            ),
            {"confirm": "on"},
        )

        self.assertTrue(
            ApplicationAttachment.objects.filter(pk=attachment.pk).exists()
        )
