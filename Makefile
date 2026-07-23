PYTHON ?= ./.venv/bin/python
TEST_PARALLEL ?= 4
DEPLOY_CHECK_SECRET_KEY ?= J7a!Nq8gP2zV4xR6tY0uL3mS5wC9dF1hK7bQ2nM4pX8rT6vW1yZ
DOCKER ?= docker
TEST_IMAGE ?= vimer:test

.PHONY: check check-deploy compile lint migrations-check compose-config \
	test test-fast test-coverage verify-fast test-docker security-scan

check:
	READ_DOT_ENV_FILE=False DEBUG=True $(PYTHON) manage.py check

lint:
	$(PYTHON) -m ruff check apps config manage.py

# Valida la postura de despliegue real (perfil production con TLS); el perfil
# pilot sin TLS reporta warnings W004/W006/W008/W012/W016 por diseño.
check-deploy:
	READ_DOT_ENV_FILE=False DEBUG=False DEPLOYMENT_PROFILE=production \
		DATABASE_URL='postgresql://vimer:test-password@localhost:5432/vimer' \
		SECRET_KEY='$(DEPLOY_CHECK_SECRET_KEY)' \
		ALLOWED_HOSTS='vimer.example.test' \
		CSRF_TRUSTED_ORIGINS='https://vimer.example.test' \
		PUBLIC_BASE_URL='https://vimer.example.test' \
		TURNSTILE_REQUIRED=True \
		TURNSTILE_SITE_KEY='test-site-key' \
		TURNSTILE_SECRET_KEY='test-secret-key' \
		EMAIL_DELIVERY_REQUIRED=True \
		EMAIL_HOST='smtp.example.test' \
		EMAIL_HOST_USER='test-user@example.test' \
		EMAIL_HOST_PASSWORD='test-password' \
		DEFAULT_FROM_EMAIL='noreply@example.test' \
		LEGAL_CONTROLLER_NAME='Test controller' \
		LEGAL_CONTROLLER_ID='Test ID' \
		LEGAL_CONTROLLER_ADDRESS='Test address' \
		LEGAL_CONTROLLER_CONTACT_CHANNEL='Test channel' \
		PRIVACY_EMAIL='privacy@example.test' \
		$(PYTHON) manage.py check --deploy

compile:
	READ_DOT_ENV_FILE=False $(PYTHON) -m compileall -q manage.py config apps

migrations-check:
	READ_DOT_ENV_FILE=False DEBUG=True $(PYTHON) manage.py makemigrations \
		--check --dry-run

compose-config:
	VIMER_DOMAIN='vimer.example.test' \
		TLS_CERTIFICATE_PATH='/tmp/vimer-fullchain.pem' \
		TLS_PRIVATE_KEY_PATH='/tmp/vimer-privkey.pem' \
		POSTGRES_PASSWORD='compose-validation-only' \
		docker-compose -f docker-compose.yml config --quiet
	VIMER_DOMAIN='vimer.example.test' \
		TLS_CERTIFICATE_PATH='/tmp/vimer-fullchain.pem' \
		TLS_PRIVATE_KEY_PATH='/tmp/vimer-privkey.pem' \
		POSTGRES_PASSWORD='compose-validation-only' \
		docker-compose -f docker-compose.pilot.yml config --quiet
	VIMER_DOMAIN='vimer.example.test' \
		TLS_CERTIFICATE_PATH='/tmp/vimer-fullchain.pem' \
		TLS_PRIVATE_KEY_PATH='/tmp/vimer-privkey.pem' \
		POSTGRES_PASSWORD='compose-validation-only' \
		docker-compose -f docker-compose.production.yml config --quiet

test:
	READ_DOT_ENV_FILE=False $(PYTHON) manage.py test

test-fast:
	READ_DOT_ENV_FILE=False $(PYTHON) manage.py test --parallel $(TEST_PARALLEL)

test-coverage:
	READ_DOT_ENV_FILE=False $(PYTHON) -m coverage run manage.py test
	$(PYTHON) -m coverage report

verify-fast: compile lint check check-deploy migrations-check test-fast

# Run the full suite inside the lightweight Debian-slim image defined by the
# Dockerfile (python:3.12-alpine3.23). Useful when the local filesystem is
# mounted noexec and cannot load compiled extensions (e.g. Pillow) directly.
test-docker:
	$(DOCKER) build -t $(TEST_IMAGE) .
	$(DOCKER) run --rm \
		-e READ_DOT_ENV_FILE=False \
		-e DEBUG=True \
		-e RUN_STARTUP_TASKS=False \
		-e DATABASE_URL=sqlite:////app/data/test.sqlite3 \
		$(TEST_IMAGE) \
		python manage.py test --parallel $(TEST_PARALLEL)

security-scan:
	sh deploy/ops/security_scan.sh
