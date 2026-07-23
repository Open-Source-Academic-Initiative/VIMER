"""Opt-in browser accessibility checks with axe-core.

The suite is deliberately opt-in because Selenium and axe-core are development
tools, not runtime dependencies.  It always runs against Django's disposable
test database and the project's isolated test-media runner.

Example (all paths may point to disposable installations under ``/tmp``)::

    RUN_AXE_TESTS=1 \
    FIREFOX_BINARY=/snap/firefox/current/usr/lib/firefox/firefox \
    AXE_SCRIPT_PATH=/tmp/vimer-a11y-node/node_modules/axe-core/axe.min.js \
    python manage.py test apps.identity.test_wcag_axe
"""

import json
import os
import unittest
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils import timezone

from apps.corporate.models import Organization
from apps.marketplace.models import Application, Challenge, ChallengeCategory

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:  # pragma: no cover - exercised only in the opt-in environment.
    webdriver = None


RUN_AXE_TESTS = os.environ.get("RUN_AXE_TESTS") == "1"
AXE_SCRIPT_PATH = Path(os.environ.get("AXE_SCRIPT_PATH", ""))
AXE_TAGS = tuple(
    tag.strip()
    for tag in os.environ.get(
        "AXE_TAGS",
        "wcag2a,wcag2aa,wcag21a,wcag21aa,wcag22a,wcag22aa",
    ).split(",")
    if tag.strip()
)


@unittest.skipUnless(
    RUN_AXE_TESTS and webdriver is not None and AXE_SCRIPT_PATH.is_file(),
    "Set RUN_AXE_TESTS=1, install Selenium and provide AXE_SCRIPT_PATH.",
)
class AxeWcag2AATests(StaticLiveServerTestCase):
    """Audit representative public and authenticated flows at WCAG 2 AA."""

    host = "127.0.0.1"
    axe_tags = AXE_TAGS

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.axe_source = AXE_SCRIPT_PATH.read_text(encoding="utf-8")
        options = Options()
        options.add_argument("-headless")
        firefox_binary = os.environ.get("FIREFOX_BINARY")
        if firefox_binary:
            options.binary_location = firefox_binary
        cls.browser = webdriver.Firefox(options=options)
        cls.browser.set_window_size(1366, 900)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.browser.quit()
        finally:
            super().tearDownClass()

    def setUp(self):
        self.browser.delete_all_cookies()
        self.browser.set_window_size(1366, 900)
        demand = Organization.objects.create(
            tax_id="900800001",
            business_name="Convocante accesible",
            chamber_of_commerce_record="CC-ACCESS-DEMAND",
            role=Organization.MarketRole.DEMAND_SIDE,
            contact_email="convocante@example.test",
            contact_phone="3000000001",
        )
        supply = Organization.objects.create(
            tax_id="900800002",
            business_name="Proveedor accesible",
            chamber_of_commerce_record="CC-ACCESS-SUPPLY",
            role=Organization.MarketRole.SUPPLY_SIDE,
            contact_email="proveedor@example.test",
            contact_phone="3000000002",
        )
        user_model = get_user_model()
        self.demand_user = user_model.objects.create_user(
            username="axe-demand",
            email="axe-demand@example.test",
            password="StrongPassword123!",
            organization=demand,
            status=user_model.AccountStatus.ACTIVE,
            is_active=True,
            is_email_verified=True,
            is_organization_titular=True,
        )
        self.supply_user = user_model.objects.create_user(
            username="axe-supply",
            email="axe-supply@example.test",
            password="StrongPassword123!",
            organization=supply,
            status=user_model.AccountStatus.ACTIVE,
            is_active=True,
            is_email_verified=True,
            is_organization_titular=True,
        )
        category, _ = ChallengeCategory.objects.get_or_create(
            slug="inteligencia-artificial",
            defaults={"name": "Inteligencia artificial"},
        )
        self.challenge = Challenge.objects.create(
            publisher=demand,
            title="Optimización energética de instalaciones",
            description=(
                "Se busca una solución medible que reduzca el consumo energético sin afectar la continuidad operativa."
            ),
            evaluation_criteria=("Viabilidad técnica | 60\nValor económico de la oferta | 40"),
            status=Challenge.Status.PUBLISHED,
            application_deadline=timezone.localdate() + timedelta(days=30),
            budget_amount=Decimal("250000000.00"),
            budget_currency=Challenge.Currency.COP,
        )
        self.challenge.categories.add(category)
        Application.objects.create(
            challenge=self.challenge,
            applicant=supply,
            problem_understanding="Borrador de entendimiento.",
            proposed_solution="Borrador de solución.",
            status=Application.Status.DRAFT,
        )

    def _open(self, path):
        self.browser.get(f"{self.live_server_url}{path}")
        WebDriverWait(self.browser, 10).until(
            lambda browser: browser.execute_script("return document.readyState") == "complete"
        )

    def _login(self, user):
        self._open(reverse("login"))
        self.browser.find_element(By.NAME, "username").send_keys(user.username)
        self.browser.find_element(By.NAME, "password").send_keys("StrongPassword123!")
        self.browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        WebDriverWait(self.browser, 10).until(lambda browser: "/login/" not in browser.current_url)

    def _logout(self):
        self.browser.find_element(
            By.CSS_SELECTOR,
            "form[action$='/logout/'] button[type='submit']",
        ).click()
        WebDriverWait(self.browser, 10).until(lambda browser: "/login/" in browser.current_url)

    def _axe_violations(self):
        self.browser.execute_script(self.axe_source)
        return self.browser.execute_async_script(
            """
            const done = arguments[arguments.length - 1];
            axe.run(document, {
                runOnly: {
                    type: "tag",
                    values: arguments[0],
                },
            }).then(
                results => done(results.violations),
                error => done([{id: "axe-runtime", impact: "critical",
                    description: String(error), nodes: []}]),
            );
            """,
            list(self.axe_tags),
        )

    @staticmethod
    def _format_violations(page_name, violations):
        details = []
        for violation in violations:
            nodes = [
                {
                    "target": node.get("target"),
                    "failure_summary": node.get("failureSummary"),
                }
                for node in violation.get("nodes", [])
            ]
            details.append(
                {
                    "page": page_name,
                    "id": violation.get("id"),
                    "impact": violation.get("impact"),
                    "description": violation.get("description"),
                    "nodes": nodes,
                }
            )
        return details

    def _audit(self, page_name, path):
        self._open(path)
        viewport = self.browser.execute_script(
            """
            return {
                clientWidth: document.documentElement.clientWidth,
                scrollWidth: document.documentElement.scrollWidth,
            };
            """
        )
        self.assertLessEqual(
            viewport["scrollWidth"],
            viewport["clientWidth"] + 1,
            (
                f"{page_name} introduces horizontal page scrolling: "
                f"{viewport['scrollWidth']} px over a "
                f"{viewport['clientWidth']} px viewport."
            ),
        )
        violations = self._axe_violations()
        self.assertFalse(
            violations,
            json.dumps(
                self._format_violations(page_name, violations),
                ensure_ascii=False,
                indent=2,
            ),
        )

    def test_representative_public_and_authenticated_pages(self):
        public_pages = (
            ("inicio", reverse("home")),
            ("inicio de sesión", reverse("login")),
            ("registro", reverse("signup")),
            ("recuperar contraseña", reverse("password_reset")),
            ("listado de desafíos", reverse("marketplace:challenge-list")),
            (
                "detalle público del desafío",
                reverse(
                    "marketplace:challenge-detail",
                    args=[self.challenge.pk],
                ),
            ),
            ("términos", reverse("legal-terms")),
            ("política de datos", reverse("legal-privacy-policy")),
            ("preguntas frecuentes", reverse("faq")),
        )
        for page_name, path in public_pages:
            with self.subTest(page=page_name):
                self._audit(page_name, path)

        self._login(self.demand_user)
        demand_pages = (
            ("panel de desafíos", reverse("marketplace:my-challenges")),
            ("formulario de desafío", reverse("marketplace:challenge-create")),
            (
                "detalle del convocante",
                reverse(
                    "marketplace:challenge-detail",
                    args=[self.challenge.pk],
                ),
            ),
            ("gobierno de organización", reverse("organization-join-requests")),
            ("notificaciones del convocante", reverse("notifications:list")),
        )
        for page_name, path in demand_pages:
            with self.subTest(page=page_name):
                self._audit(page_name, path)
        self._logout()

        self._login(self.supply_user)
        supply_pages = (
            ("panel de propuestas", reverse("marketplace:my-applications")),
            (
                "formulario de propuesta",
                reverse(
                    "marketplace:challenge-apply",
                    args=[self.challenge.pk],
                ),
            ),
            (
                "detalle del proveedor",
                reverse(
                    "marketplace:challenge-detail",
                    args=[self.challenge.pk],
                ),
            ),
            ("notificaciones del proveedor", reverse("notifications:list")),
        )
        for page_name, path in supply_pages:
            with self.subTest(page=page_name):
                self._audit(page_name, path)
        self._logout()

    def test_representative_mobile_reflow(self):
        self.browser.set_window_size(390, 844)
        public_pages = (
            ("inicio móvil", reverse("home")),
            ("registro móvil", reverse("signup")),
            ("listado móvil", reverse("marketplace:challenge-list")),
            (
                "detalle público móvil",
                reverse(
                    "marketplace:challenge-detail",
                    args=[self.challenge.pk],
                ),
            ),
        )
        for page_name, path in public_pages:
            with self.subTest(page=page_name):
                self._audit(page_name, path)

        self._login(self.demand_user)
        for page_name, path in (
            ("panel de desafíos móvil", reverse("marketplace:my-challenges")),
            ("formulario de desafío móvil", reverse("marketplace:challenge-create")),
        ):
            with self.subTest(page=page_name):
                self._audit(page_name, path)
        self._logout()

        self._login(self.supply_user)
        for page_name, path in (
            ("panel de propuestas móvil", reverse("marketplace:my-applications")),
            (
                "formulario de propuesta móvil",
                reverse(
                    "marketplace:challenge-apply",
                    args=[self.challenge.pk],
                ),
            ),
        ):
            with self.subTest(page=page_name):
                self._audit(page_name, path)
        self._logout()
