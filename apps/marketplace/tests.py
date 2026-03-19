import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from apps.corporate.avatar_utils import generate_default_logo
from apps.corporate.models import Organization
from apps.marketplace.application.commands import SubmitApplicationCommand
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.application.services import submit_challenge_application
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
        )

    def test_challenge_create_page_loads_for_demand_side_user(self):
        self.client.force_login(self.demand_user)

        response = self.client.get(reverse("marketplace:challenge-create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "marketplace/challenge_form.html")

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

    def test_challenge_apply_duplicate_submission_shows_duplicate_message(self):
        Application.objects.create(
            challenge=self.challenge,
            applicant=self.supply_organization,
            proposal_text="Initial proposal",
        )
        self.client.force_login(self.supply_user)

        response = self.client.post(
            reverse("marketplace:challenge-apply", args=[self.challenge.pk]),
            {"proposal_text": "Second proposal"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            None,
            "Tu organización ya envió una propuesta para este desafío.",
        )

    def test_challenge_detail_shows_applicant_logo_for_publisher(self):
        Application.objects.create(
            challenge=self.challenge,
            applicant=self.supply_organization,
            proposal_text="Initial proposal",
        )
        self.client.force_login(self.demand_user)

        response = self.client.get(
            reverse("marketplace:challenge-detail", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.supply_organization.logo.url)


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
        )

    def test_submit_application_rejects_duplicates(self):
        command = SubmitApplicationCommand(proposal_text="Initial proposal")

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
        command = SubmitApplicationCommand(proposal_text="Proposal")

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
