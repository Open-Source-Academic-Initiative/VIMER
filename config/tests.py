import os
import sqlite3
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
from deploy.ops.sqlite_restore import main as sqlite_restore


class SQLiteRestoreTests(SimpleTestCase):
    def test_restore_recovers_data_and_preserves_operational_permissions(self):
        with TemporaryDirectory(prefix="vimer-restore-test-") as directory:
            backup = Path(directory) / "backup.sqlite3"
            target = Path(directory) / "db.sqlite3"
            with sqlite3.connect(backup) as database:
                database.execute("CREATE TABLE example (value TEXT)")
                database.execute("INSERT INTO example VALUES ('original')")
            with sqlite3.connect(target) as database:
                database.execute("CREATE TABLE example (value TEXT)")
                database.execute("INSERT INTO example VALUES ('changed')")
            backup.chmod(0o600)
            target.chmod(0o640)
            owner = (target.stat().st_uid, target.stat().st_gid)
            with patch.object(sys, "argv", ["sqlite_restore.py", str(backup), str(target)]):
                self.assertEqual(sqlite_restore(), 0)
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)
            self.assertEqual((target.stat().st_uid, target.stat().st_gid), owner)
            with sqlite3.connect(target) as database:
                self.assertEqual(database.execute("SELECT value FROM example").fetchone(), ("original",))


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
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    )
    def test_admin_login_has_the_same_brute_force_limit_as_public_login(self):
        cache.clear()
        middleware = RateLimitMiddleware(lambda request: HttpResponse("ok"))
        factory = RequestFactory()
        limit, _ = settings.RATE_LIMIT_RULES["/login/"]
        responses = [middleware(factory.post("/admin/login/", REMOTE_ADDR="192.0.2.11"))
                     for _ in range(limit + 1)]
        self.assertEqual(responses[-1].status_code, 429)

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
    def production_environment(self, database_url):
        return {
            "DEBUG": "False", "DEPLOYMENT_PROFILE": "production",
            "DATABASE_URL": database_url,
            "SECRET_KEY": "J7a!Nq8gP2zV4xR6tY0uL3mS5wC9dF1hK7bQ2nM4pX8rT6vW1yZ",
            "ALLOWED_HOSTS": "vimer.example.test",
            "CSRF_TRUSTED_ORIGINS": "https://vimer.example.test",
            "PUBLIC_BASE_URL": "https://vimer.example.test",
            "TURNSTILE_REQUIRED": "True", "TURNSTILE_SITE_KEY": "test-site-key",
            "TURNSTILE_SECRET_KEY": "test-secret-key",
            "EMAIL_DELIVERY_REQUIRED": "True", "EMAIL_HOST": "smtp.example.test",
            "EMAIL_HOST_USER": "test-user@example.test", "EMAIL_HOST_PASSWORD": "test-password",
            "DEFAULT_FROM_EMAIL": "noreply@example.test",
            "LEGAL_CONTROLLER_NAME": "Responsable de prueba", "LEGAL_CONTROLLER_ID": "ID de prueba",
            "LEGAL_CONTROLLER_ADDRESS": "Dirección de prueba",
            "LEGAL_CONTROLLER_CONTACT_CHANNEL": "Canal de prueba", "PRIVACY_EMAIL": "privacy@example.test",
        }

    def test_production_accepts_both_supported_database_backends(self):
        for url in ("sqlite:////tmp/vimer-config-test.sqlite3", "postgresql://vimer:test@localhost/vimer"):
            with self.subTest(url=url):
                result = self.run_settings_import(**self.production_environment(url))
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_database_choice_does_not_disable_production_security_gates(self):
        for url in ("sqlite:////tmp/vimer-config-test.sqlite3", "postgresql://vimer:test@localhost/vimer"):
            for variable, value, message in (
                ("DEBUG", "True", "DEBUG must be False"),
                ("SECRET_KEY", "short", "Production SECRET_KEY"),
                ("SECURE_SSL_REDIRECT", "False", "Production security settings"),
                ("TURNSTILE_REQUIRED", "False", "TURNSTILE_REQUIRED cannot be disabled"),
                ("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend", "console email backend"),
            ):
                with self.subTest(url=url, variable=variable):
                    environment = self.production_environment(url)
                    environment[variable] = value
                    result = self.run_settings_import(**environment)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(message, result.stderr)

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
