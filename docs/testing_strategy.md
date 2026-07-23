# Testing Strategy

## Purpose

This document captures the current automated-validation strategy for VIMER and the practical guidance for running the Django 6.0 test suite efficiently.

## Current approach

The suite combines:

- flow-level tests for web behavior and permissions
- service-level tests for application-layer use cases
- model and validation tests for persistence invariants
- static validation through `compileall`
- Django configuration checks through `manage.py check` and `manage.py check --deploy`

The suite currently holds 144 tests and passes green both locally and inside the Debian-slim container image.

## Runtime optimization strategy

The current optimization is intentionally conservative and Django-native:

- heavy immutable fixtures were moved from `setUp()` to `setUpTestData()` where safe
- per-test `setUp()` is now limited to lightweight ORM refreshes for mutable shared objects
- test execution ignores the local workspace `.env` by default through `READ_DOT_ENV_FILE=False`
- the default fast path uses Django's multiprocess runner through `manage.py test --parallel`
- the suite now covers persisted application drafts, draft-to-submitted promotion, and draft privacy across marketplace, evaluation, and notifications

This project's tests are primarily database- and ORM-bound. In this profile:

- process-level parallelism helps
- thread-level parallelism is not a meaningful gain for Django's test runner
- hardware accelerators such as GPU are not relevant

## Benchmarks

Reference measurements captured on the local server profile used during the optimization work:

- historical full-suite baseline before the fixture refactor: `396.022s`
- optimized sequential run: `56.357s`
- earlier optimized parallel run with `--parallel 2`: `32.090s`
- earlier best measured optimized parallel run with `--parallel 4`: `30.723s`
- latest full validation after the current documentation audit with `--parallel 4`: `38.974s`

Observed wall-clock timings including database setup/teardown:

- `manage.py test`: `58.91s`
- `manage.py test --parallel 2`: `34.68s`
- `manage.py test --parallel 4`: `33.63s`

These numbers confirm that Django's multiprocess runner is materially better than the sequential path on this host, but they no longer prove that `--parallel 4` is always faster than `--parallel 2` for the current suite shape. Keep `TEST_PARALLEL=4` as the repository default for now, and rerun the benchmark whenever suite composition or hardware profile changes enough to matter.

## Standard commands

The repository now provides a small `Makefile`:

```bash
make test
make test-fast
make verify-fast
make test-docker
```

Notes:

- `make test-fast` defaults to `TEST_PARALLEL=4`
- override the worker count with `make test-fast TEST_PARALLEL=2`
- `make verify-fast` runs static compilation, Django checks, deploy checks, and the fast parallel suite
- `make test-docker` builds the multi-stage `python:3.12-slim-trixie` image from the `Dockerfile` and runs the full suite inside the container; use it when the working tree lives on a `noexec` mount (e.g. an NFS-mounted home) where compiled extensions such as Pillow cannot be loaded directly. Pass `DOCKER="sudo docker"` when the Docker socket needs privileges.
- in-container reference run on the pilot host: `Ran 144 tests in 87.043s` (single worker-friendly default; the build also resolved the latest in-range dependency patches and stayed green)

## Manual QA validation

Automated tests are complemented by a manual QA pass for the v1 pilot flows.
A single idempotent management command seeds a complete set of accounts that
cover every role and account state (platform superuser, Solicitante titular and
designated evaluation-team members, a pending join request, two Proveedor
titulares, and an email-unverified account for the operate-after-verification
gate):

```bash
python manage.py seed_categories
python manage.py seed_test_users
```

The seeder is for QA/staging only and must not be run on a real
participant-facing instance. Credentials and manual test records are
environment-local operational material and are intentionally not versioned.

## Maintenance guidance

When adding or refactoring tests:

- prefer `setUpTestData()` for immutable fixtures reused across methods
- keep mutations inside each test or refresh shared ORM instances in `setUp()`
- avoid expensive repeated media-generation or object-graph creation when it can be shared safely
- keep invariant coverage traceable across service tests and flow tests
- when a physical Django app holds more than one concern, keep the tests split by subdomain ownership instead of rebuilding one generic suite bucket

## Files most impacted by the optimization

- `apps/evaluation/tests.py`
- `apps/notifications/tests.py`
- `apps/marketplace/tests.py`
- `apps/identity/tests.py`
