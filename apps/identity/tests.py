from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.identity.application.commands import RegisterOrganizationUserCommand
from apps.identity.application.services import register_organization_user


class RegistrationFlowTests(TestCase):
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
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = get_user_model().objects.get(username="new_user")
        self.assertEqual(user.organization.business_name, "New Org")
        self.assertEqual(user.organization.contact_phone, "3001234567")

    def test_signup_rejects_duplicate_tax_id_as_form_error(self):
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
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "tax_id",
            "Ya existe una organización registrada con este NIT.",
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


class RegistrationApplicationServiceTests(TestCase):
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
