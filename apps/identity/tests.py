from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class RegistrationFlowTests(TestCase):
    def test_signup_creates_user_and_organization(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "nuevo_usuario",
                "email": "nuevo@example.com",
                "first_name": "Nuevo",
                "last_name": "Usuario",
                "nit": "900123456",
                "business_name": "Org Nueva",
                "chamber_of_commerce": "CC-123",
                "role": "OFERENTE",
                "contact_phone": "3001234567",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = get_user_model().objects.get(username="nuevo_usuario")
        self.assertEqual(user.organization.business_name, "Org Nueva")
        self.assertEqual(user.organization.contact_phone, "3001234567")

    def test_signup_rejects_duplicate_nit_as_form_error(self):
        self.client.post(
            reverse("signup"),
            {
                "username": "primer_usuario",
                "email": "primer@example.com",
                "first_name": "Primer",
                "last_name": "Usuario",
                "nit": "900999999",
                "business_name": "Org Base",
                "chamber_of_commerce": "CC-BASE",
                "role": "OFERENTE",
                "contact_phone": "3000000000",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
            },
        )

        response = self.client.post(
            reverse("signup"),
            {
                "username": "segundo_usuario",
                "email": "segundo@example.com",
                "first_name": "Segundo",
                "last_name": "Usuario",
                "nit": "900999999",
                "business_name": "Org Duplicada",
                "chamber_of_commerce": "CC-DUP",
                "role": "OFERENTE",
                "contact_phone": "3111111111",
                "password": "ClaveSegura123",
                "confirm_password": "ClaveSegura123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "nit",
            "Ya existe una organización registrada con este NIT.",
        )

    def test_signup_rejects_weak_password(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "usuario_debil",
                "email": "debil@example.com",
                "first_name": "Debil",
                "last_name": "Password",
                "nit": "901234567",
                "business_name": "Org Debil",
                "chamber_of_commerce": "CC-WEAK",
                "role": "OFERENTE",
                "contact_phone": "3222222222",
                "password": "123",
                "confirm_password": "123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="usuario_debil").exists())
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
