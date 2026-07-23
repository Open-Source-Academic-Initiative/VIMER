import json
import shutil
import smtplib
import tempfile
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.admin import helpers
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from PIL import Image

from apps.corporate.models import Organization
from apps.identity.application.commands import RegisterOrganizationUserCommand
from apps.identity.application.exceptions import (
    DuplicateEmailError,
    DuplicateUsernameError,
    RegistrationValidationError,
)
from apps.identity.application.services import register_organization_user
from apps.identity.models import (
    EmailVerificationToken,
    IdentityAuditEntry,
    OrganizationJoinRequest,
)
from apps.marketplace.models import Application, Challenge
from apps.notifications.models import Notification


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
        self.assertContains(response, "Desafíos reales. Soluciones que avanzan.")

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

        self.assertRedirects(response, reverse("signup-done"))
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

        self.assertRedirects(response, reverse("signup-done"))
        user = get_user_model().objects.get(username="logo_user")
        self.assertTrue(user.organization.logo.name.lower().endswith(".png"))

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

        self.assertRedirects(response, reverse("signup-done"))
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

    def test_join_registration_emits_audit_and_notifies_operational_titular(self):
        organization = Organization.objects.create(
            tax_id="902400001",
            business_name="Existing Join Org",
            chamber_of_commerce_record="CC-SVC-JOIN",
            role="SUPPLY_SIDE",
            contact_email="existing-join@example.com",
            contact_phone="3004440001",
        )
        titular = get_user_model().objects.create_user(
            username="existing_join_titular",
            email="existing-join-titular@example.com",
            password="ClaveSegura123",
            organization=organization,
            is_organization_titular=True,
            is_email_verified=True,
        )

        with self.captureOnCommitCallbacks(execute=True):
            requester = register_organization_user(
                RegisterOrganizationUserCommand(
                    username="joining_service_user",
                    email="joining-service-user@example.com",
                    first_name="Joining",
                    last_name="User",
                    password="ClaveSegura123",
                    tax_id=organization.tax_id,
                    business_name=organization.business_name,
                    chamber_of_commerce_record="IGNORED",
                    role="SUPPLY_SIDE",
                    contact_phone="3004440002",
                )
            )

        join_request = OrganizationJoinRequest.objects.get(requester=requester)
        self.assertTrue(
            IdentityAuditEntry.objects.filter(
                event_type=IdentityAuditEntry.EventType.REPRESENTATIVE_JOIN_REQUESTED,
                join_request=join_request,
                subject=requester,
            ).exists()
        )
        notification = Notification.objects.get(
            recipient=titular,
            kind=Notification.Kind.REPRESENTATIVE_JOIN_REQUESTED,
        )
        self.assertEqual(
            notification.link,
            reverse("organization-join-requests"),
        )

    def test_failed_join_registration_never_deletes_existing_organization_logo(self):
        organization = Organization.objects.create(
            tax_id="902400002",
            business_name="Existing Logo Org",
            chamber_of_commerce_record="CC-SVC-LOGO",
            role="SUPPLY_SIDE",
            contact_email="existing-logo@example.com",
            contact_phone="3004440003",
            logo=self.make_test_image(
                image_format="PNG",
                filename="active-logo.png",
            ),
        )
        logo_name = organization.logo.name
        with organization.logo.storage.open(logo_name, "rb") as logo_file:
            logo_before = logo_file.read()

        with patch(
            "apps.identity.application.services.send_mail",
            side_effect=smtplib.SMTPException("smtp unavailable"),
        ):
            with self.assertRaises(RegistrationValidationError):
                register_organization_user(
                    RegisterOrganizationUserCommand(
                        username="failed_joining_user",
                        email="failed-joining-user@example.com",
                        first_name="Failed",
                        last_name="Joining",
                        password="ClaveSegura123",
                        tax_id=organization.tax_id,
                        business_name=organization.business_name,
                        chamber_of_commerce_record="IGNORED",
                        role="SUPPLY_SIDE",
                        contact_phone="3004440004",
                    )
                )

        self.assertTrue(organization.logo.storage.exists(logo_name))
        with organization.logo.storage.open(logo_name, "rb") as logo_file:
            self.assertEqual(logo_file.read(), logo_before)
        self.assertFalse(
            get_user_model()
            .objects.filter(username="failed_joining_user")
            .exists()
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


class EmailVerificationFlowTests(MediaRootIsolatedTestCase):
    def _signup_payload(self, **overrides):
        payload = {
            "username": "verify_user",
            "email": "verify@example.com",
            "first_name": "Verify",
            "last_name": "User",
            "tax_id": "900500100",
            "business_name": "Verify Org",
            "chamber_of_commerce": "CC-VER",
            "role": "SUPPLY_SIDE",
            "contact_phone": "3001112222",
            "password": "ClaveSegura123",
            "confirm_password": "ClaveSegura123",
            "accept_terms": "on",
            "accept_privacy_policy": "on",
        }
        payload.update(overrides)
        return payload

    @override_settings(PUBLIC_BASE_URL="https://vimer.example.org")
    def test_signup_sends_verification_email_with_absolute_url(self):
        mail.outbox = []

        response = self.client.post(reverse("signup"), self._signup_payload())

        self.assertRedirects(response, reverse("signup-done"))
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("https://vimer.example.org/verificar-correo/", body)
        user = get_user_model().objects.get(username="verify_user")
        self.assertFalse(user.is_email_verified)

    def test_verification_link_get_requires_confirmation_without_consuming_token(self):
        user = get_user_model().objects.create_user(
            username="to_confirm",
            email="to-confirm@example.com",
            password="ClaveSegura123",
        )
        token = EmailVerificationToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.get(reverse("verify-email", args=[token.token]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["verified"])
        self.assertTrue(response.context["confirmation_required"])
        user.refresh_from_db()
        self.assertFalse(user.is_email_verified)
        token.refresh_from_db()
        self.assertIsNone(token.used_at)

    def test_verification_confirmation_post_marks_email_verified(self):
        user = get_user_model().objects.create_user(
            username="to_verify",
            email="to-verify@example.com",
            password="ClaveSegura123",
        )
        token = EmailVerificationToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.post(reverse("verify-email", args=[token.token]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["verified"])
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        token.refresh_from_db()
        self.assertIsNotNone(token.used_at)

    def test_invalid_token_does_not_verify(self):
        response = self.client.get(reverse("verify-email", args=["nonexistent-token"]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["verified"])

    def test_expired_token_does_not_verify(self):
        user = get_user_model().objects.create_user(
            username="expired_user",
            email="expired@example.com",
            password="ClaveSegura123",
        )
        token = EmailVerificationToken.objects.create(
            user=user,
            expires_at=timezone.now() - timedelta(hours=1),
        )

        response = self.client.get(reverse("verify-email", args=[token.token]))

        self.assertFalse(response.context["verified"])
        user.refresh_from_db()
        self.assertFalse(user.is_email_verified)

    def test_used_token_cannot_be_reused(self):
        user = get_user_model().objects.create_user(
            username="used_user",
            email="used@example.com",
            password="ClaveSegura123",
        )
        token = EmailVerificationToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(days=1),
            used_at=timezone.now(),
        )

        response = self.client.get(reverse("verify-email", args=[token.token]))

        self.assertFalse(response.context["verified"])

    def test_signup_rolls_back_when_verification_email_fails(self):
        files_before = {
            path.relative_to(self._media_root)
            for path in Path(self._media_root).rglob("*")
            if path.is_file()
        }
        with patch(
            "apps.identity.application.services.send_mail",
            side_effect=smtplib.SMTPException("smtp unavailable"),
        ):
            response = self.client.post(
                reverse("signup"),
                self._signup_payload(
                    username="rollback_user",
                    email="rollback@example.com",
                    tax_id="900500999",
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(username="rollback_user").exists()
        )
        self.assertFalse(Organization.objects.filter(tax_id="900500999").exists())
        files_after = {
            path.relative_to(self._media_root)
            for path in Path(self._media_root).rglob("*")
            if path.is_file()
        }
        self.assertEqual(files_after, files_before)


class EmailVerificationGatingTests(MediaRootIsolatedTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = Organization.objects.create(
            tax_id="900600100",
            business_name="Gating Org",
            chamber_of_commerce_record="CC-GATE",
            role="DEMAND_SIDE",
            contact_email="gate@example.com",
            contact_phone="3000000000",
        )
        User = get_user_model()
        cls.verified_user = User.objects.create_user(
            username="verified_demand",
            email="verified-demand@example.com",
            password="ClaveSegura123",
            organization=cls.organization,
            is_email_verified=True,
        )
        cls.unverified_user = User.objects.create_user(
            username="unverified_demand",
            email="unverified-demand@example.com",
            password="ClaveSegura123",
            organization=cls.organization,
            is_email_verified=False,
        )

    def test_unverified_user_is_redirected_from_challenge_create(self):
        self.client.force_login(self.unverified_user)

        response = self.client.get(reverse("marketplace:challenge-create"))

        self.assertRedirects(response, reverse("marketplace:challenge-list"))

    def test_unverified_user_cannot_post_challenge(self):
        self.client.force_login(self.unverified_user)

        response = self.client.post(reverse("marketplace:challenge-create"), {})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Challenge.objects.filter(publisher=self.organization).count(), 0
        )

    def test_verified_user_can_open_challenge_create(self):
        self.client.force_login(self.verified_user)

        response = self.client.get(reverse("marketplace:challenge-create"))

        self.assertEqual(response.status_code, 200)


class EmailVerificationResendTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            tax_id="900600200",
            business_name="Resend Org",
            chamber_of_commerce_record="CC-RESEND",
            role="SUPPLY_SIDE",
            contact_email="resend@example.com",
            contact_phone="3000000001",
        )
        self.user = get_user_model().objects.create_user(
            username="resend_user",
            email="resend-user@example.com",
            password="ClaveSegura123",
            organization=self.organization,
            is_email_verified=False,
        )
        self.previous_token = EmailVerificationToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(days=1),
        )

    def test_post_replaces_outstanding_token_and_sends_email(self):
        self.client.force_login(self.user)
        mail.outbox = []

        response = self.client.post(reverse("resend-email-verification"))

        self.assertRedirects(response, reverse("home"))
        self.previous_token.refresh_from_db()
        self.assertIsNotNone(self.previous_token.used_at)
        usable_tokens = [
            token
            for token in EmailVerificationToken.objects.filter(user=self.user)
            if token.is_usable
        ]
        self.assertEqual(len(usable_tokens), 1)
        self.assertNotEqual(usable_tokens[0].pk, self.previous_token.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(usable_tokens[0].token, mail.outbox[0].body)

    def test_verified_account_gets_same_neutral_response_without_new_email(self):
        self.user.is_email_verified = True
        self.user.save(update_fields=["is_email_verified"])
        self.client.force_login(self.user)
        mail.outbox = []

        response = self.client.post(
            reverse("resend-email-verification"),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Si tu cuenta requiere verificación",
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(
            EmailVerificationToken.objects.filter(user=self.user).count(),
            1,
        )

    def test_delivery_failure_preserves_previous_usable_token(self):
        self.client.force_login(self.user)

        with patch(
            "apps.identity.application.services.send_mail",
            side_effect=smtplib.SMTPException("smtp unavailable"),
        ):
            response = self.client.post(
                reverse("resend-email-verification"),
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Si tu cuenta requiere verificación",
        )
        self.previous_token.refresh_from_db()
        self.assertTrue(self.previous_token.is_usable)
        self.assertEqual(
            EmailVerificationToken.objects.filter(user=self.user).count(),
            1,
        )

    def test_endpoint_is_post_only_and_requires_authentication(self):
        response = self.client.get(reverse("resend-email-verification"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

        self.client.force_login(self.user)
        response = self.client.get(reverse("resend-email-verification"))
        self.assertEqual(response.status_code, 405)


class OperationalMembershipBoundaryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.publisher = Organization.objects.create(
            tax_id="900650100",
            business_name="Boundary Publisher",
            chamber_of_commerce_record="CC-BOUNDARY-P",
            role="DEMAND_SIDE",
            contact_email="boundary-publisher@example.com",
            contact_phone="3000000100",
        )
        self.provider = Organization.objects.create(
            tax_id="900650200",
            business_name="Boundary Provider",
            chamber_of_commerce_record="CC-BOUNDARY-S",
            role="SUPPLY_SIDE",
            contact_email="boundary-provider@example.com",
            contact_phone="3000000200",
        )
        self.operational_user = User.objects.create_user(
            username="boundary_operational",
            email="boundary-operational@example.com",
            password="ClaveSegura123",
            organization=self.publisher,
            is_email_verified=True,
        )
        self.pending_user = User.objects.create_user(
            username="boundary_pending",
            email="boundary-pending@example.com",
            password="ClaveSegura123",
            organization=self.publisher,
            status=User.AccountStatus.PENDING_APPROVAL,
            is_email_verified=True,
        )
        self.rejected_user = User.objects.create_user(
            username="boundary_rejected",
            email="boundary-rejected@example.com",
            password="ClaveSegura123",
            organization=self.publisher,
            status=User.AccountStatus.INACTIVE,
            is_email_verified=True,
        )
        self.expired_user = User.objects.create_user(
            username="boundary_expired",
            email="boundary-expired@example.com",
            password="ClaveSegura123",
            organization=self.publisher,
            status=User.AccountStatus.INACTIVE,
            is_email_verified=True,
        )
        self.unverified_user = User.objects.create_user(
            username="boundary_unverified",
            email="boundary-unverified@example.com",
            password="ClaveSegura123",
            organization=self.publisher,
            is_email_verified=False,
        )
        self.challenge = Challenge.objects.create(
            publisher=self.publisher,
            title="Confidential boundary challenge",
            description="Descripción pública",
            evaluation_criteria="Viabilidad",
            status=Challenge.Status.PUBLISHED,
            application_deadline=timezone.localdate() + timedelta(days=5),
        )
        Application.objects.create(
            challenge=self.challenge,
            applicant=self.provider,
            status=Application.Status.SUBMITTED,
            proposal_text="PROPUESTA-SECRETA-BOUNDARY",
            problem_understanding="Entendimiento secreto",
            proposed_solution="Solución secreta",
            capabilities_evidence="Capacidades secretas",
            execution_plan="Plan secreto",
        )
        Notification.objects.create(
            recipient=self.pending_user,
            kind=Notification.Kind.EVALUATION_STARTED,
            title="Notificación privada",
            body="Contenido privado",
        )

    def test_operational_queryset_is_the_single_membership_scope(self):
        operational_ids = set(
            get_user_model().objects.operational().values_list("pk", flat=True)
        )

        self.assertEqual(operational_ids, {self.operational_user.pk})
        self.assertTrue(
            self.operational_user.is_operational_member_of(self.publisher)
        )
        self.assertFalse(self.pending_user.is_operational_member_of(self.publisher))
        self.assertFalse(self.rejected_user.can_operate)
        self.assertFalse(self.expired_user.can_operate)
        self.assertFalse(self.unverified_user.can_operate)

    def test_non_operational_states_cannot_read_organization_proposals(self):
        for user in (
            self.pending_user,
            self.rejected_user,
            self.expired_user,
            self.unverified_user,
        ):
            with self.subTest(username=user.username):
                self.client.logout()
                self.client.force_login(user)
                response = self.client.get(
                    reverse(
                        "marketplace:challenge-detail",
                        args=[self.challenge.pk],
                    )
                )

                self.assertNotIn(
                    b"PROPUESTA-SECRETA-BOUNDARY",
                    response.content,
                )

    def test_pending_user_cannot_read_or_mutate_notification_inbox(self):
        self.client.force_login(self.pending_user)

        list_response = self.client.get(reverse("notifications:list"))
        mark_response = self.client.post(reverse("notifications:mark-all-read"))

        self.assertRedirects(list_response, reverse("home"))
        self.assertRedirects(mark_response, reverse("home"))
        self.assertIsNone(
            Notification.objects.get(recipient=self.pending_user).read_at
        )


class OrganizationJoinExpirationCommandTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.organization = Organization.objects.create(
            tax_id="900690100",
            business_name="Expiry Org",
            chamber_of_commerce_record="CC-EXPIRY",
            role="SUPPLY_SIDE",
            contact_email="expiry@example.com",
            contact_phone="3000000900",
        )
        self.due_requester = User.objects.create_user(
            username="expiry_due",
            email="expiry-due@example.com",
            password="ClaveSegura123",
            organization=self.organization,
            status=User.AccountStatus.PENDING_APPROVAL,
            is_email_verified=True,
        )
        self.future_requester = User.objects.create_user(
            username="expiry_future",
            email="expiry-future@example.com",
            password="ClaveSegura123",
            organization=self.organization,
            status=User.AccountStatus.PENDING_APPROVAL,
            is_email_verified=True,
        )
        self.due_request = OrganizationJoinRequest.objects.create(
            organization=self.organization,
            requester=self.due_requester,
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        self.future_request = OrganizationJoinRequest.objects.create(
            organization=self.organization,
            requester=self.future_requester,
            expires_at=timezone.now() + timedelta(days=1),
        )

    def test_command_expires_only_due_requests_and_is_idempotent(self):
        output = StringIO()
        with self.captureOnCommitCallbacks(execute=True):
            call_command("expire_join_requests", stdout=output)

        self.due_request.refresh_from_db()
        self.future_request.refresh_from_db()
        self.due_requester.refresh_from_db()
        self.future_requester.refresh_from_db()
        self.assertEqual(
            self.due_request.status,
            OrganizationJoinRequest.Status.EXPIRED,
        )
        self.assertFalse(self.due_requester.is_active)
        self.assertEqual(
            self.future_request.status,
            OrganizationJoinRequest.Status.PENDING,
        )
        self.assertTrue(self.future_requester.is_active)
        self.assertIn("Expired 1 join requests.", output.getvalue())
        self.assertEqual(
            IdentityAuditEntry.objects.filter(
                event_type=IdentityAuditEntry.EventType.REPRESENTATIVE_JOIN_EXPIRED,
                join_request=self.due_request,
            ).count(),
            1,
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.due_requester,
                kind=Notification.Kind.REPRESENTATIVE_JOIN_EXPIRED,
            ).exists()
        )

        second_output = StringIO()
        with self.captureOnCommitCallbacks(execute=True):
            call_command("expire_join_requests", stdout=second_output)

        self.assertIn("Expired 0 join requests.", second_output.getvalue())
        self.assertEqual(
            IdentityAuditEntry.objects.filter(
                event_type=IdentityAuditEntry.EventType.REPRESENTATIVE_JOIN_EXPIRED,
                join_request=self.due_request,
            ).count(),
            1,
        )


class OrganizationJoinRequestDecisionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.organization = Organization.objects.create(
            tax_id="900700100",
            business_name="Join Org",
            chamber_of_commerce_record="CC-JOIN",
            role="SUPPLY_SIDE",
            contact_email="join@example.com",
            contact_phone="3000000000",
        )
        self.titular = User.objects.create_user(
            username="join_titular",
            email="join-titular@example.com",
            password="ClaveSegura123",
            organization=self.organization,
            is_organization_titular=True,
            is_email_verified=True,
        )
        self.active_member = User.objects.create_user(
            username="join_member",
            email="join-member@example.com",
            password="ClaveSegura123",
            organization=self.organization,
            is_email_verified=True,
        )
        self.requester = User.objects.create_user(
            username="join_requester",
            email="join-requester@example.com",
            password="ClaveSegura123",
            organization=self.organization,
            status=User.AccountStatus.PENDING_APPROVAL,
            is_email_verified=True,
        )
        self.join_request = OrganizationJoinRequest.objects.create(
            organization=self.organization,
            requester=self.requester,
            expires_at=timezone.now() + timedelta(days=14),
        )

    def test_titular_approves_request(self):
        self.client.force_login(self.titular)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse(
                    "organization-join-request-approve",
                    kwargs={"pk": self.join_request.pk},
                )
            )

        self.assertRedirects(response, reverse("organization-join-requests"))
        self.join_request.refresh_from_db()
        self.requester.refresh_from_db()
        self.assertEqual(
            self.join_request.status, OrganizationJoinRequest.Status.APPROVED
        )
        self.assertEqual(
            self.requester.status, get_user_model().AccountStatus.ACTIVE
        )
        self.assertTrue(self.requester.is_active)
        self.assertTrue(self.requester.can_operate)
        self.assertTrue(
            IdentityAuditEntry.objects.filter(
                event_type=IdentityAuditEntry.EventType.REPRESENTATIVE_JOIN_APPROVED,
                join_request=self.join_request,
                actor=self.titular,
                subject=self.requester,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.requester,
                kind=Notification.Kind.REPRESENTATIVE_JOIN_APPROVED,
            ).exists()
        )

    def test_titular_rejects_request(self):
        self.client.force_login(self.titular)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse(
                    "organization-join-request-reject",
                    kwargs={"pk": self.join_request.pk},
                )
            )

        self.assertRedirects(response, reverse("organization-join-requests"))
        self.join_request.refresh_from_db()
        self.requester.refresh_from_db()
        self.assertEqual(
            self.join_request.status, OrganizationJoinRequest.Status.REJECTED
        )
        self.assertEqual(
            self.requester.status, get_user_model().AccountStatus.INACTIVE
        )
        self.assertFalse(self.requester.is_active)
        self.assertFalse(self.requester.can_operate)
        self.assertTrue(
            IdentityAuditEntry.objects.filter(
                event_type=IdentityAuditEntry.EventType.REPRESENTATIVE_JOIN_REJECTED,
                join_request=self.join_request,
                actor=self.titular,
                subject=self.requester,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.requester,
                kind=Notification.Kind.REPRESENTATIVE_JOIN_REJECTED,
            ).exists()
        )

    def test_expired_request_cannot_be_approved_and_is_closed_atomically(self):
        self.join_request.expires_at = timezone.now() - timedelta(seconds=1)
        self.join_request.save(update_fields=["expires_at"])
        self.client.force_login(self.titular)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse(
                    "organization-join-request-approve",
                    kwargs={"pk": self.join_request.pk},
                )
            )

        self.assertRedirects(response, reverse("organization-join-requests"))
        self.join_request.refresh_from_db()
        self.requester.refresh_from_db()
        self.assertEqual(
            self.join_request.status,
            OrganizationJoinRequest.Status.EXPIRED,
        )
        self.assertEqual(
            self.requester.status,
            get_user_model().AccountStatus.INACTIVE,
        )
        self.assertFalse(self.requester.is_active)
        self.assertFalse(
            IdentityAuditEntry.objects.filter(
                event_type=IdentityAuditEntry.EventType.REPRESENTATIVE_JOIN_APPROVED,
                join_request=self.join_request,
            ).exists()
        )
        self.assertTrue(
            IdentityAuditEntry.objects.filter(
                event_type=IdentityAuditEntry.EventType.REPRESENTATIVE_JOIN_EXPIRED,
                join_request=self.join_request,
            ).exists()
        )

    def test_unverified_titular_cannot_decide_request(self):
        self.titular.is_email_verified = False
        self.titular.save(update_fields=["is_email_verified"])
        self.client.force_login(self.titular)

        response = self.client.post(
            reverse(
                "organization-join-request-approve",
                kwargs={"pk": self.join_request.pk},
            )
        )

        self.assertEqual(response.status_code, 403)
        self.join_request.refresh_from_db()
        self.assertEqual(
            self.join_request.status,
            OrganizationJoinRequest.Status.PENDING,
        )

    def test_non_titular_cannot_open_request_list(self):
        self.client.force_login(self.active_member)

        response = self.client.get(reverse("organization-join-requests"))

        self.assertEqual(response.status_code, 403)

    def test_titular_cannot_decide_request_from_another_organization(self):
        other_organization = Organization.objects.create(
            tax_id="900700200",
            business_name="Other Join Org",
            chamber_of_commerce_record="CC-JOIN2",
            role="SUPPLY_SIDE",
            contact_email="join2@example.com",
            contact_phone="3000000001",
        )
        other_titular = get_user_model().objects.create_user(
            username="other_titular",
            email="other-titular@example.com",
            password="ClaveSegura123",
            organization=other_organization,
            is_organization_titular=True,
            is_email_verified=True,
        )
        self.client.force_login(other_titular)

        response = self.client.post(
            reverse(
                "organization-join-request-approve",
                kwargs={"pk": self.join_request.pk},
            )
        )

        self.assertRedirects(response, reverse("organization-join-requests"))
        self.join_request.refresh_from_db()
        self.assertEqual(
            self.join_request.status, OrganizationJoinRequest.Status.PENDING
        )


class OrganizationTitularityTransferViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.organization = Organization.objects.create(
            tax_id="900800100",
            business_name="Titular Org",
            chamber_of_commerce_record="CC-TIT",
            role="SUPPLY_SIDE",
            contact_email="tit@example.com",
            contact_phone="3000000000",
        )
        self.titular = User.objects.create_user(
            username="current_titular",
            email="current-titular@example.com",
            password="ClaveSegura123",
            organization=self.organization,
            is_organization_titular=True,
            is_email_verified=True,
        )
        self.active_member = User.objects.create_user(
            username="active_member",
            email="active-member@example.com",
            password="ClaveSegura123",
            organization=self.organization,
            is_email_verified=True,
        )

    def test_titular_transfers_titularity_to_active_member(self):
        self.client.force_login(self.titular)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("organization-titularity-transfer"),
                {
                    "target_user_id": self.active_member.pk,
                    "confirm_transfer": "yes",
                },
            )

        # The former titular loses access to the titular-only list page, so we
        # assert the redirect target without fetching it.
        self.assertRedirects(
            response,
            reverse("organization-join-requests"),
            fetch_redirect_response=False,
        )
        self.titular.refresh_from_db()
        self.active_member.refresh_from_db()
        self.assertFalse(self.titular.is_organization_titular)
        self.assertTrue(self.active_member.is_organization_titular)
        self.assertTrue(
            IdentityAuditEntry.objects.filter(
                event_type=(
                    IdentityAuditEntry.EventType.ORGANIZATION_OWNERSHIP_TRANSFERRED
                ),
                organization=self.organization,
                actor=self.titular,
                subject=self.active_member,
            ).exists()
        )
        self.assertEqual(
            Notification.objects.filter(
                kind=Notification.Kind.ORGANIZATION_OWNERSHIP_TRANSFERRED,
                recipient__in=[self.titular, self.active_member],
            ).count(),
            2,
        )
        self.assertEqual(
            Notification.objects.get(
                kind=Notification.Kind.ORGANIZATION_OWNERSHIP_TRANSFERRED,
                recipient=self.titular,
            ).link,
            reverse("home"),
        )
        self.assertEqual(
            Notification.objects.get(
                kind=Notification.Kind.ORGANIZATION_OWNERSHIP_TRANSFERRED,
                recipient=self.active_member,
            ).link,
            reverse("organization-join-requests"),
        )

    def test_cannot_transfer_to_inactive_member(self):
        self.active_member.status = get_user_model().AccountStatus.INACTIVE
        self.active_member.save(update_fields=["status"])
        self.client.force_login(self.titular)

        response = self.client.post(
            reverse("organization-titularity-transfer"),
            {
                "target_user_id": self.active_member.pk,
                "confirm_transfer": "yes",
            },
        )

        self.assertRedirects(response, reverse("organization-join-requests"))
        self.titular.refresh_from_db()
        self.assertTrue(self.titular.is_organization_titular)

    def test_cannot_transfer_to_unverified_member(self):
        self.active_member.is_email_verified = False
        self.active_member.save(update_fields=["is_email_verified"])
        self.client.force_login(self.titular)

        response = self.client.post(
            reverse("organization-titularity-transfer"),
            {
                "target_user_id": self.active_member.pk,
                "confirm_transfer": "yes",
            },
        )

        self.assertRedirects(response, reverse("organization-join-requests"))
        self.titular.refresh_from_db()
        self.active_member.refresh_from_db()
        self.assertTrue(self.titular.is_organization_titular)
        self.assertFalse(self.active_member.is_organization_titular)

    def test_transfer_requires_explicit_server_side_confirmation(self):
        self.client.force_login(self.titular)

        response = self.client.post(
            reverse("organization-titularity-transfer"),
            {"target_user_id": self.active_member.pk},
        )

        self.assertRedirects(response, reverse("organization-join-requests"))
        self.titular.refresh_from_db()
        self.active_member.refresh_from_db()
        self.assertTrue(self.titular.is_organization_titular)
        self.assertFalse(self.active_member.is_organization_titular)
        self.assertFalse(
            IdentityAuditEntry.objects.filter(
                event_type=(
                    IdentityAuditEntry.EventType.ORGANIZATION_OWNERSHIP_TRANSFERRED
                ),
                organization=self.organization,
            ).exists()
        )


class PasswordResetFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reset_user",
            email="reset-user@example.com",
            password="ClaveSegura123",
        )

    def test_password_reset_sends_email_with_link(self):
        mail.outbox = []

        response = self.client.post(
            reverse("password_reset"), {"email": "reset-user@example.com"}
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/reset/", mail.outbox[0].body)

    def test_password_reset_confirm_sets_new_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        self.client.get(
            reverse(
                "password_reset_confirm",
                kwargs={"uidb64": uid, "token": token},
            )
        )

        response = self.client.post(
            reverse(
                "password_reset_confirm",
                kwargs={"uidb64": uid, "token": "set-password"},
            ),
            {"new_password1": "NuevaClave456", "new_password2": "NuevaClave456"},
        )

        self.assertRedirects(response, reverse("password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NuevaClave456"))

    def test_password_reset_for_unknown_email_sends_nothing(self):
        mail.outbox = []

        response = self.client.post(
            reverse("password_reset"), {"email": "unknown@example.com"}
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)


class TurnstileVerificationTests(MediaRootIsolatedTestCase):
    def _command(self, **overrides):
        defaults = {
            "username": "turnstile_user",
            "email": "turnstile@example.com",
            "first_name": "Turnstile",
            "last_name": "User",
            "password": "ClaveSegura123",
            "tax_id": "900900100",
            "business_name": "Turnstile Org",
            "chamber_of_commerce_record": "CC-TURN",
            "role": "SUPPLY_SIDE",
            "contact_phone": "3000000000",
            "turnstile_token": "token-from-widget",
        }
        defaults.update(overrides)
        return RegisterOrganizationUserCommand(**defaults)

    def _turnstile_response(self, *, success):
        response = MagicMock()
        response.read.return_value = json.dumps({"success": success}).encode()
        context_manager = MagicMock()
        context_manager.__enter__.return_value = response
        return context_manager

    @override_settings(TURNSTILE_SECRET_KEY="secret")
    def test_registration_fails_when_turnstile_is_rejected(self):
        with patch(
            "apps.identity.application.services.urlopen",
            return_value=self._turnstile_response(success=False),
        ):
            with self.assertRaises(RegistrationValidationError):
                register_organization_user(self._command())

        self.assertFalse(
            get_user_model().objects.filter(username="turnstile_user").exists()
        )

    @override_settings(TURNSTILE_SECRET_KEY="secret")
    def test_registration_passes_when_turnstile_is_accepted(self):
        with patch(
            "apps.identity.application.services.urlopen",
            return_value=self._turnstile_response(success=True),
        ):
            user = register_organization_user(self._command())

        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())

    @override_settings(TURNSTILE_SITE_KEY="site-key")
    def test_signup_form_requires_turnstile_token(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "no_turnstile",
                "email": "no-turnstile@example.com",
                "first_name": "No",
                "last_name": "Turnstile",
                "tax_id": "900900200",
                "business_name": "No Turnstile Org",
                "chamber_of_commerce": "CC-NOTURN",
                "role": "SUPPLY_SIDE",
                "contact_phone": "3000000000",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
                "accept_terms": "on",
                "accept_privacy_policy": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(
            get_user_model().objects.filter(username="no_turnstile").exists()
        )


class PlatformDashboardTests(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_superuser(
            username="dash_admin",
            email="dash-admin@example.com",
            password="ClaveSegura123",
        )
        self.regular_user = get_user_model().objects.create_user(
            username="dash_regular",
            email="dash-regular@example.com",
            password="ClaveSegura123",
        )

    def test_dashboard_requires_staff(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("platform-dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_dashboard_renders_kpis_for_staff(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse("platform-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/platform_dashboard.html")
        self.assertIn("organization_count", response.context)
        self.assertIn("submitted_application_count", response.context)

    def test_active_representative_kpi_counts_only_operational_members(self):
        organization = Organization.objects.create(
            tax_id="900910100",
            business_name="Dashboard Membership Org",
            chamber_of_commerce_record="CC-DASH-MEMBERSHIP",
            role="SUPPLY_SIDE",
            contact_email="dashboard-membership@example.com",
            contact_phone="3009100100",
        )
        User = get_user_model()
        User.objects.create_user(
            username="dashboard_operational",
            email="dashboard-operational@example.com",
            password="ClaveSegura123",
            organization=organization,
            is_email_verified=True,
        )
        User.objects.create_user(
            username="dashboard_pending",
            email="dashboard-pending@example.com",
            password="ClaveSegura123",
            organization=organization,
            status=User.AccountStatus.PENDING_APPROVAL,
            is_email_verified=True,
        )
        User.objects.create_user(
            username="dashboard_unverified",
            email="dashboard-unverified@example.com",
            password="ClaveSegura123",
            organization=organization,
            is_email_verified=False,
        )
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse("platform-dashboard"))

        self.assertEqual(response.context["active_representative_count"], 1)
