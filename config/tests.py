import os
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from config.context_processors import public_settings
from config.security import RateLimitMiddleware
from deploy.scheduler_healthcheck import main as scheduler_healthcheck


class HealthEndpointTests(TestCase):
    def test_liveness_does_not_depend_on_database_state(self):
        response = self.client.get(reverse("health-live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(
            response["Cache-Control"],
            "max-age=0, no-cache, no-store, must-revalidate, private",
        )

    def test_readiness_checks_database_and_migrations(self):
        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "database": "ok",
                "migrations": "ok",
            },
        )


class RateLimitMiddlewareTests(SimpleTestCase):
    @override_settings(
        RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_RULES={"/login/": (2, 60)},
        TRUST_PROXY_CLIENT_IP=False,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "vimer-rate-limit-tests",
            }
        },
    )
    def test_rejects_requests_after_configured_limit(self):
        cache.clear()
        middleware = RateLimitMiddleware(lambda request: HttpResponse("ok"))
        factory = RequestFactory()

        responses = [
            middleware(factory.post("/login/", REMOTE_ADDR="192.0.2.10"))
            for _ in range(3)
        ]

        self.assertEqual(
            [response.status_code for response in responses],
            [200, 200, 429],
        )
        self.assertEqual(responses[-1]["Retry-After"], "60")


class PublicSettingsTests(SimpleTestCase):
    @override_settings(
        LEGAL_CONTROLLER_NAME="Controlador de prueba",
        LEGAL_CONTROLLER_ID="ID de prueba",
        LEGAL_CONTROLLER_ADDRESS="Dirección de prueba",
        LEGAL_CONTROLLER_CONTACT_CHANNEL="Canal de prueba",
        PRIVACY_EMAIL="privacidad@example.test",
    )
    def test_exposes_configurable_legal_controller_data(self):
        context = public_settings(RequestFactory().get("/"))

        self.assertEqual(context["legal_controller_name"], "Controlador de prueba")
        self.assertEqual(context["legal_controller_id"], "ID de prueba")
        self.assertEqual(context["legal_controller_address"], "Dirección de prueba")
        self.assertEqual(
            context["legal_controller_contact_channel"],
            "Canal de prueba",
        )
        self.assertEqual(context["privacy_email"], "privacidad@example.test")


class MediaIsolationTests(SimpleTestCase):
    def test_global_runner_uses_disposable_media_root(self):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        operational_media_root = (settings.BASE_DIR / "media").resolve()

        self.assertNotEqual(media_root, operational_media_root)
        self.assertTrue(media_root.name.startswith("vimer-test-media-"))

        proof_file = media_root / "isolation-proof.txt"
        proof_file.write_text("test-only", encoding="utf-8")
        self.assertTrue(proof_file.is_file())


class DeploymentSettingsFailFastTests(SimpleTestCase):
    environment_names = {
        "DEBUG",
        "DEPLOYMENT_PROFILE",
        "EMAIL_BACKEND",
        "EMAIL_DELIVERY_REQUIRED",
        "EMAIL_HOST",
        "EMAIL_HOST_PASSWORD",
        "EMAIL_HOST_USER",
        "DEFAULT_FROM_EMAIL",
        "READ_DOT_ENV_FILE",
        "SECRET_KEY",
        "TURNSTILE_REQUIRED",
        "TURNSTILE_SECRET_KEY",
        "TURNSTILE_SITE_KEY",
    }

    def run_settings_import(self, **overrides):
        environment = os.environ.copy()
        for variable_name in self.environment_names:
            environment.pop(variable_name, None)
        environment.update(
            {
                "DEBUG": "False",
                "DEPLOYMENT_PROFILE": "pilot",
                "READ_DOT_ENV_FILE": "False",
                "SECRET_KEY": "pilot-settings-test-secret",
            }
        )
        environment.update(overrides)
        return subprocess.run(
            [
                sys.executable,
                "-c",
                "import config.settings; print('settings-loaded')",
            ],
            cwd=settings.BASE_DIR,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_pilot_without_turnstile_keys_fails_closed(self):
        result = self.run_settings_import()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Turnstile keys are required", result.stderr)

    def test_pilot_without_smtp_configuration_fails_closed(self):
        result = self.run_settings_import(
            TURNSTILE_SITE_KEY="test-site-key",
            TURNSTILE_SECRET_KEY="test-secret-key",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SMTP delivery requires", result.stderr)

    def test_isolated_maintenance_mode_requires_explicit_opt_outs(self):
        result = self.run_settings_import(
            TURNSTILE_REQUIRED="False",
            EMAIL_DELIVERY_REQUIRED="False",
            EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("settings-loaded", result.stdout)


class SchedulerHealthcheckTests(SimpleTestCase):
    def test_accepts_recent_successful_heartbeat(self):
        with TemporaryDirectory(prefix="vimer-scheduler-test-") as directory:
            heartbeat_path = Path(directory) / "heartbeat"
            heartbeat_path.write_text(
                (
                    f"join_requests={int(time.time())}\n"
                    f"challenges={int(time.time())}\n"
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "SCHEDULER_HEARTBEAT_PATH": str(heartbeat_path),
                    "JOIN_REQUEST_EXPIRY_INTERVAL_SECONDS": "60",
                    "CHALLENGE_CLOSURE_INTERVAL_SECONDS": "120",
                    "SCHEDULER_HEALTH_GRACE_SECONDS": "60",
                },
            ):
                self.assertEqual(scheduler_healthcheck(), 0)

    def test_rejects_heartbeat_when_either_job_is_stale(self):
        with TemporaryDirectory(prefix="vimer-scheduler-test-") as directory:
            heartbeat_path = Path(directory) / "heartbeat"
            heartbeat_path.write_text(
                f"join_requests={int(time.time())}\nchallenges=1\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "SCHEDULER_HEARTBEAT_PATH": str(heartbeat_path),
                    "JOIN_REQUEST_EXPIRY_INTERVAL_SECONDS": "60",
                    "CHALLENGE_CLOSURE_INTERVAL_SECONDS": "60",
                    "SCHEDULER_HEALTH_GRACE_SECONDS": "60",
                },
            ):
                self.assertEqual(scheduler_healthcheck(), 1)
