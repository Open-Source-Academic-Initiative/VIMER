import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.contrib.admin import helpers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from PIL import Image

from apps.corporate.models import Organization
from apps.identity.application.commands import RegisterOrganizationUserCommand
from apps.identity.application.exceptions import (
    DuplicateEmailError,
    DuplicateUsernameError,
    RegistrationValidationError,
)
from apps.identity.application.services import register_organization_user
from apps.identity.models import OrganizationJoinRequest


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

    def make_test_image(
        self,
        *,
        image_format: str,
        filename: str,
        color: tuple[int, int, int] = (32, 96, 160),
    ) -> SimpleUploadedFile:
        image = Image.new("RGB", (32, 32), color)
        buffer = BytesIO()
        image.save(buffer, format=image_format)
        content_type_map = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "GIF": "image/gif",
        }
        return SimpleUploadedFile(
            filename,
            buffer.getvalue(),
            content_type=content_type_map[image_format],
        )


class RegistrationFlowTests(MediaRootIsolatedTestCase):
    def test_home_loads_landing_page(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "landing.html")
        self.assertContains(response, "Conecta desafíos con soluciones")

    def test_signup_creates_user_and_organization(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "new_user",
                "email": "nuevo@example.com",
                "first_name": "New",
                "last_name": "User",
                "tax_id": "900123456",
                "business_name": "New Org",
                "chamber_of_commerce": "CC-123",
                "role": "SUPPLY_SIDE",
                "contact_phone": "3001234567",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
                "accept_terms": "on",
                "accept_privacy_policy": "on",
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = get_user_model().objects.get(username="new_user")
        self.assertEqual(user.organization.business_name, "New Org")
        self.assertEqual(user.organization.contact_phone, "3001234567")
        self.assertTrue(user.organization.logo.name.endswith(".png"))
        self.assertTrue(user.organization.logo.storage.exists(user.organization.logo.name))

    def test_signup_accepts_custom_jpg_logo(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "logo_user",
                "email": "logo@example.com",
                "first_name": "Logo",
                "last_name": "User",
                "tax_id": "900123457",
                "business_name": "Logo Org",
                "chamber_of_commerce": "CC-124",
                "role": "SUPPLY_SIDE",
                "contact_phone": "3001234568",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
                "accept_terms": "on",
                "accept_privacy_policy": "on",
                "logo": self.make_test_image(
                    image_format="JPEG",
                    filename="custom-logo.jpg",
                ),
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = get_user_model().objects.get(username="logo_user")
        self.assertTrue(
            user.organization.logo.name.lower().endswith((".jpg", ".jpeg"))
        )

    def test_signup_rejects_non_png_or_jpg_logo(self):
        invalid_logo = self.make_test_image(
            image_format="GIF",
            filename="custom-logo.gif",
        )

        response = self.client.post(
            reverse("signup"),
            {
                "username": "invalid_logo_user",
                "email": "invalid-logo@example.com",
                "first_name": "Invalid",
                "last_name": "Logo",
                "tax_id": "900123458",
                "business_name": "Invalid Logo Org",
                "chamber_of_commerce": "CC-125",
                "role": "SUPPLY_SIDE",
                "contact_phone": "3001234569",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
                "accept_terms": "on",
                "accept_privacy_policy": "on",
                "logo": invalid_logo,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "logo",
            "Solo se permiten imagenes PNG o JPG.",
        )
        self.assertFalse(
            get_user_model().objects.filter(username="invalid_logo_user").exists()
        )

    def test_organization_logo_validator_also_applies_at_model_level(self):
        organization = Organization(
            tax_id="900123459",
            business_name="Model Validation Org",
            chamber_of_commerce_record="CC-126",
            role="SUPPLY_SIDE",
            contact_email="model-validation@example.com",
            contact_phone="3001234570",
            logo=self.make_test_image(
                image_format="GIF",
                filename="invalid-model-logo.gif",
            ),
        )

        with self.assertRaises(ValidationError) as captured:
            organization.full_clean()

        self.assertIn("Solo se permiten imagenes PNG o JPG.", captured.exception.message_dict["logo"])

    def test_signup_existing_tax_id_creates_pending_join_request(self):
        self.client.post(
            reverse("signup"),
            {
                "username": "first_user",
                "email": "first@example.com",
                "first_name": "First",
                "last_name": "User",
                "tax_id": "900999999",
                "business_name": "Base Org",
                "chamber_of_commerce": "CC-BASE",
                "role": "SUPPLY_SIDE",
                "contact_phone": "3000000000",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
                "accept_terms": "on",
                "accept_privacy_policy": "on",
            },
        )

        response = self.client.post(
            reverse("signup"),
            {
                "username": "second_user",
                "email": "second@example.com",
                "first_name": "Second",
                "last_name": "User",
                "tax_id": "900999999",
                "business_name": "Duplicate Org",
                "chamber_of_commerce": "CC-DUP",
                "role": "SUPPLY_SIDE",
                "contact_phone": "3111111111",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
                "accept_terms": "on",
                "accept_privacy_policy": "on",
            },
        )

        self.assertRedirects(response, reverse("login"))
        first_user = get_user_model().objects.get(username="first_user")
        second_user = get_user_model().objects.get(username="second_user")
        self.assertEqual(second_user.organization, first_user.organization)
        self.assertEqual(second_user.status, get_user_model().AccountStatus.PENDING_APPROVAL)
        self.assertFalse(second_user.is_organization_titular)
        self.assertTrue(
            OrganizationJoinRequest.objects.filter(
                organization=first_user.organization,
                requester=second_user,
                status=OrganizationJoinRequest.Status.PENDING,
            ).exists()
        )

    def test_signup_rejects_duplicate_username_as_form_error(self):
        existing_org = Organization.objects.create(
            tax_id="900777001",
            business_name="Existing Username Org",
            chamber_of_commerce_record="CC-USER",
            role="SUPPLY_SIDE",
            contact_email="existing-username-org@example.com",
            contact_phone="3007770001",
        )
        get_user_model().objects.create_user(
            username="existing_user",
            email="existing-user@example.com",
            password="ClaveSegura123",
            organization=existing_org,
        )

        response = self.client.post(
            reverse("signup"),
            {
                "username": "existing_user",
                "email": "nuevo-username@example.com",
                "first_name": "Repeated",
                "last_name": "Username",
                "tax_id": "900777002",
                "business_name": "New Username Org",
                "chamber_of_commerce": "CC-USER-NEW",
                "role": "SUPPLY_SIDE",
                "contact_phone": "3007770002",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
                "accept_terms": "on",
                "accept_privacy_policy": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "username",
            "Ya existe un usuario registrado con este nombre de usuario.",
        )

    def test_signup_rejects_duplicate_email_as_form_error(self):
        existing_org = Organization.objects.create(
            tax_id="900888001",
            business_name="Existing Email Org",
            chamber_of_commerce_record="CC-EMAIL",
            role="SUPPLY_SIDE",
            contact_email="existing-email-org@example.com",
            contact_phone="3008880001",
        )
        get_user_model().objects.create_user(
            username="existing_email_user",
            email="existing-email@example.com",
            password="ClaveSegura123",
            organization=existing_org,
        )

        response = self.client.post(
            reverse("signup"),
            {
                "username": "new_email_user",
                "email": "existing-email@example.com",
                "first_name": "Repeated",
                "last_name": "Email",
                "tax_id": "900888002",
                "business_name": "New Email Org",
                "chamber_of_commerce": "CC-EMAIL-NEW",
                "role": "SUPPLY_SIDE",
                "contact_phone": "3008880002",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
                "accept_terms": "on",
                "accept_privacy_policy": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "Ya existe un usuario registrado con este correo electrónico.",
        )

    def test_signup_rejects_duplicate_email_case_insensitively_as_form_error(self):
        existing_org = Organization.objects.create(
            tax_id="900889001",
            business_name="Existing Case Email Org",
            chamber_of_commerce_record="CC-EMAIL-CASE",
            role="SUPPLY_SIDE",
            contact_email="existing-case-email-org@example.com",
            contact_phone="3008890001",
        )
        get_user_model().objects.create_user(
            username="existing_case_email_user",
            email="Existing-Email@Example.com",
            password="ClaveSegura123",
            organization=existing_org,
        )

        response = self.client.post(
            reverse("signup"),
            {
                "username": "new_case_email_user",
                "email": "existing-email@example.com",
                "first_name": "Repeated",
                "last_name": "CaseEmail",
                "tax_id": "900889002",
                "business_name": "New Case Email Org",
                "chamber_of_commerce": "CC-EMAIL-CASE-NEW",
                "role": "SUPPLY_SIDE",
                "contact_phone": "3008890002",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
                "accept_terms": "on",
                "accept_privacy_policy": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "Ya existe un usuario registrado con este correo electrónico.",
        )

    def test_signup_rejects_weak_password(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "weak_user",
                "email": "debil@example.com",
                "first_name": "Weak",
                "last_name": "Password",
                "tax_id": "901234567",
                "business_name": "Weak Org",
                "chamber_of_commerce": "CC-WEAK",
                "role": "SUPPLY_SIDE",
                "contact_phone": "3222222222",
                "password": "123",
                "confirm_password": "123",
                "accept_terms": "on",
                "accept_privacy_policy": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="weak_user").exists())
        self.assertTrue(response.context["form"].errors.get("password"))

    def test_logout_requires_post_and_redirects(self):
        user = get_user_model().objects.create_user(
            username="logout_user",
            email="logout@example.com",
            password="ClaveSegura123",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))

    @patch("apps.identity.views.register_organization_user")
    def test_signup_surfaces_service_validation_errors_as_form_errors(self, mocked_register):
        mocked_register.side_effect = RegistrationValidationError(
            message_dict={"contact_email": ["Formato de correo inválido desde el servicio."]},
        )

        response = self.client.post(
            reverse("signup"),
            {
                "username": "candidate_user",
                "email": "candidate@example.com",
                "first_name": "Candidate",
                "last_name": "User",
                "tax_id": "901999999",
                "business_name": "Candidate Org",
                "chamber_of_commerce": "CC-CAND",
                "role": "SUPPLY_SIDE",
                "contact_phone": "3009999999",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
                "accept_terms": "on",
                "accept_privacy_policy": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "Formato de correo inválido desde el servicio.",
        )


class RegistrationApplicationServiceTests(MediaRootIsolatedTestCase):
    def test_register_organization_user_creates_aggregate(self):
        user = register_organization_user(
            RegisterOrganizationUserCommand(
                username="service_user",
                email="service@example.com",
                first_name="Service",
                last_name="User",
                password="ClaveSegura123",
                tax_id="902000001",
                business_name="Service Org",
                chamber_of_commerce_record="CC-SVC",
                role="SUPPLY_SIDE",
                contact_phone="3001112233",
            )
        )

        self.assertEqual(user.organization.tax_id, "902000001")
        self.assertEqual(user.organization.business_name, "Service Org")
        self.assertTrue(user.organization.logo.name.endswith(".png"))

    def test_register_organization_user_rejects_duplicate_username(self):
        existing_org = Organization.objects.create(
            tax_id="902100001",
            business_name="Existing Username Service Org",
            chamber_of_commerce_record="CC-SVC-USER",
            role="SUPPLY_SIDE",
            contact_email="svc-username-org@example.com",
            contact_phone="3001110001",
        )
        get_user_model().objects.create_user(
            username="service_duplicate_user",
            email="service-duplicate-user@example.com",
            password="ClaveSegura123",
            organization=existing_org,
        )

        with self.assertRaises(DuplicateUsernameError):
            register_organization_user(
                RegisterOrganizationUserCommand(
                    username="service_duplicate_user",
                    email="new-service-user@example.com",
                    first_name="Service",
                    last_name="DuplicateUsername",
                    password="ClaveSegura123",
                    tax_id="902100002",
                    business_name="New Username Service Org",
                    chamber_of_commerce_record="CC-SVC-USER-NEW",
                    role="SUPPLY_SIDE",
                    contact_phone="3001110002",
                )
            )

    def test_register_organization_user_rejects_duplicate_email(self):
        existing_org = Organization.objects.create(
            tax_id="902200001",
            business_name="Existing Email Service Org",
            chamber_of_commerce_record="CC-SVC-EMAIL",
            role="SUPPLY_SIDE",
            contact_email="svc-email-org@example.com",
            contact_phone="3002220001",
        )
        get_user_model().objects.create_user(
            username="service_email_user",
            email="service-duplicate-email@example.com",
            password="ClaveSegura123",
            organization=existing_org,
        )

        with self.assertRaises(DuplicateEmailError):
            register_organization_user(
                RegisterOrganizationUserCommand(
                    username="new_service_email_user",
                    email="service-duplicate-email@example.com",
                    first_name="Service",
                    last_name="DuplicateEmail",
                    password="ClaveSegura123",
                    tax_id="902200002",
                    business_name="New Email Service Org",
                    chamber_of_commerce_record="CC-SVC-EMAIL-NEW",
                    role="SUPPLY_SIDE",
                    contact_phone="3002220002",
                )
            )

    def test_register_organization_user_rejects_invalid_email_with_validation_error(self):
        with self.assertRaises(RegistrationValidationError) as captured:
            register_organization_user(
                RegisterOrganizationUserCommand(
                    username="invalid_email_user",
                    email="invalid-email",
                    first_name="Invalid",
                    last_name="Email",
                    password="ClaveSegura123",
                    tax_id="902300001",
                    business_name="Invalid Email Org",
                    chamber_of_commerce_record="CC-SVC-INVALID",
                    role="SUPPLY_SIDE",
                    contact_phone="3003330001",
                )
            )

        self.assertIn(
            "Ingrese una dirección de correo electrónico válida.",
            captured.exception.messages,
        )


class SuperuserAdminSafeguardsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="platform_admin",
            email="platform-admin@example.com",
            password="ClaveSegura123",
        )
        cls.other_user = get_user_model().objects.create_user(
            username="managed_user",
            email="managed-user@example.com",
            password="ClaveSegura123",
        )

    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.get(pk=self.admin_user.pk)
        self.other_user = User.objects.get(pk=self.other_user.pk)

    def test_superuser_cannot_delete_itself_from_admin_delete_view(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin:identity_user_delete", args=[self.admin_user.pk]),
            {"post": "yes"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            get_user_model().objects.filter(pk=self.admin_user.pk).exists()
        )

    def test_superuser_bulk_delete_skips_own_account(self):
        self.client.force_login(self.admin_user)
        selected_users = [str(self.admin_user.pk), str(self.other_user.pk)]

        confirmation_response = self.client.post(
            reverse("admin:identity_user_changelist"),
            {
                "action": "delete_selected_preserving_self",
                helpers.ACTION_CHECKBOX_NAME: selected_users,
                "index": 0,
            },
        )

        self.assertEqual(confirmation_response.status_code, 200)

        response = self.client.post(
            reverse("admin:identity_user_changelist"),
            {
                "action": "delete_selected_preserving_self",
                helpers.ACTION_CHECKBOX_NAME: selected_users,
                "post": "yes",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            get_user_model().objects.filter(pk=self.admin_user.pk).exists()
        )
        self.assertFalse(
            get_user_model().objects.filter(pk=self.other_user.pk).exists()
        )
        self.assertContains(
            response,
            "No puedes eliminarte a ti mismo desde el panel de administración.",
        )
