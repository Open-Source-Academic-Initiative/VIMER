PYTHON ?= ./.venv/bin/python
TEST_PARALLEL ?= 4
DEPLOY_CHECK_SECRET_KEY ?= J7a!Nq8gP2zV4xR6tY0uL3mS5wC9dF1hK7bQ2nM4pX8rT6vW1yZ

.PHONY: check check-deploy compile test test-fast verify-fast

check:
	READ_DOT_ENV_FILE=False DEBUG=True $(PYTHON) manage.py check

check-deploy:
	READ_DOT_ENV_FILE=False DEBUG=False SECRET_KEY='$(DEPLOY_CHECK_SECRET_KEY)' $(PYTHON) manage.py check --deploy

compile:
	READ_DOT_ENV_FILE=False $(PYTHON) -m compileall -q manage.py config apps

test:
	READ_DOT_ENV_FILE=False $(PYTHON) manage.py test

test-fast:
	READ_DOT_ENV_FILE=False $(PYTHON) manage.py test --parallel $(TEST_PARALLEL)

verify-fast: compile check check-deploy test-fast
