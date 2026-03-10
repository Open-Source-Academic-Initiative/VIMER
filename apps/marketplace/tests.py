from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.corporate.models import Organization
from apps.marketplace.models import Challenge


class MarketplaceFlowTests(TestCase):
    def setUp(self):
        self.demand_organization = Organization.objects.create(
            tax_id="900000101",
            business_name="Demand-side Test",
            chamber_of_commerce_record="CC-101",
            role="DEMAND_SIDE",
            contact_email="demand@example.com",
            contact_phone="1111111",
        )
        self.supply_organization = Organization.objects.create(
            tax_id="900000202",
            business_name="Supply-side Test",
            chamber_of_commerce_record="CC-202",
            role="SUPPLY_SIDE",
            contact_email="supply@example.com",
            contact_phone="2222222",
        )
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

    def test_challenge_apply_page_includes_challenge_context(self):
        self.client.force_login(self.supply_user)

        response = self.client.get(
            reverse("marketplace:challenge-apply", args=[self.challenge.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["challenge"], self.challenge)
