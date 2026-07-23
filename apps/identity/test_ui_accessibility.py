from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.corporate.models import Organization


class PublicInterfaceRegressionTests(TestCase):
    def test_landing_has_landmarks_brand_and_no_internal_qa_copy(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, '<main id="main-content"', html=False)
        self.assertContains(response, "Un proyecto de OpenSAI")
        self.assertContains(response, "Desafíos reales. Soluciones que avanzan.")
        self.assertNotContains(response, "Plataforma MVP")
        self.assertNotContains(response, "usuarios de prueba")
        self.assertNotContains(response, "<style")
        self.assertNotContains(response, "style=")
        policy = response.headers["Content-Security-Policy"]
        script_policy = next(
            directive
            for directive in policy.split(";")
            if directive.strip().startswith("script-src")
        )
        self.assertNotIn("'unsafe-inline'", script_policy)

    def test_login_links_native_password_reset(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, reverse("password_reset"))

    def test_invalid_password_reset_link_does_not_render_password_form(self):
        response = self.client.get(
            reverse(
                "password_reset_confirm",
                kwargs={"uidb64": "invalid", "token": "invalid-token"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este enlace no es válido")
        self.assertNotContains(response, "Guardar contraseña")
        self.assertContains(response, reverse("password_reset"))

    @override_settings(TURNSTILE_SITE_KEY="test-site-key")
    def test_turnstile_script_is_loaded_only_on_signup(self):
        landing = self.client.get(reverse("home"))
        signup = self.client.get(reverse("signup"))

        script_url = "https://challenges.cloudflare.com/turnstile/v0/api.js"
        self.assertNotContains(landing, script_url)
        self.assertContains(signup, script_url)


class MarketplaceAccessibilityRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(
            tax_id="900777001",
            business_name="Convocante accesible",
            chamber_of_commerce_record="CC-777",
            role=Organization.MarketRole.DEMAND_SIDE,
            contact_email="contacto@example.com",
            contact_phone="3000000000",
        )
        cls.user = get_user_model().objects.create_user(
            username="accessible_publisher",
            email="accessible@example.com",
            password="StrongPassword123!",
            organization=cls.organization,
            status=get_user_model().AccountStatus.ACTIVE,
            is_email_verified=True,
            is_organization_titular=True,
        )

    def test_challenge_filters_have_persistent_visible_labels(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("marketplace:challenge-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'label for="challenge-search"', html=False)
        self.assertContains(response, 'label for="challenge-category"', html=False)
        self.assertContains(response, 'label for="challenge-status"', html=False)
