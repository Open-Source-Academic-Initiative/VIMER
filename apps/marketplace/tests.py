from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.corporate.models import Organization
from apps.marketplace.models import Challenge


class MarketplaceFlowTests(TestCase):
    def setUp(self):
        self.demandante = Organization.objects.create(
            nit="900000101",
            business_name="Demandante Test",
            chamber_of_commerce_record="CC-101",
            role="DEMANDANTE",
            contact_email="demandante@example.com",
            contact_phone="1111111",
        )
        self.oferente = Organization.objects.create(
            nit="900000202",
            business_name="Oferente Test",
            chamber_of_commerce_record="CC-202",
            role="OFERENTE",
            contact_email="oferente@example.com",
            contact_phone="2222222",
        )
        self.demandante_user = get_user_model().objects.create_user(
            username="demandante_user",
            email="demandante_user@example.com",
            password="ClaveSegura123",
            organization=self.demandante,
        )
        self.oferente_user = get_user_model().objects.create_user(
            username="oferente_user",
            email="oferente_user@example.com",
            password="ClaveSegura123",
            organization=self.oferente,
        )
        self.challenge = Challenge.objects.create(
            publisher=self.demandante,
            title="Reto existente",
            description="Descripcion del reto",
        )

    def test_challenge_create_page_loads_for_demandante(self):
        self.client.force_login(self.demandante_user)

        response = self.client.get(reverse("marketplace:challenge-create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "marketplace/challenge_form.html")

    def test_challenge_apply_page_includes_challenge_context(self):
        self.client.force_login(self.oferente_user)

        response = self.client.get(
            reverse("marketplace:challenge-apply", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["challenge"], self.challenge)
