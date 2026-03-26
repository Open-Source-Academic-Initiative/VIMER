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

## Runtime optimization strategy

The current optimization is intentionally conservative and Django-native:

- heavy immutable fixtures were moved from `setUp()` to `setUpTestData()` where safe
- per-test `setUp()` is now limited to lightweight ORM refreshes for mutable shared objects
- test execution ignores the local workspace `.env` by default through `READ_DOT_ENV_FILE=False`
- the default fast path uses Django's multiprocess runner through `manage.py test --parallel`

This project's tests are primarily database- and ORM-bound. In this profile:

- process-level parallelism helps
- thread-level parallelism is not a meaningful gain for Django's test runner
- hardware accelerators such as GPU are not relevant

## Benchmarks

Measured on the current local server profile used during the optimization pass:

- historical full-suite baseline before the fixture refactor: `396.022s`
- optimized sequential run: `56.357s`
- optimized parallel run with `--parallel 2`: `32.090s`
- best measured optimized parallel run with `--parallel 4`: `30.723s`
- latest full validation after the scoring/adjudication implementation with `--parallel 4`: `31.696s`

Observed wall-clock timings including database setup/teardown:

- `manage.py test`: `58.91s`
- `manage.py test --parallel 2`: `34.68s`
- `manage.py test --parallel 4`: `33.63s`

On this host, `--parallel 4` remains the fastest measured option, although the gain over `--parallel 2` is small and normal suite evolution can move the exact runtime slightly. If the hardware profile changes, rerun the benchmark before changing the default.

## Standard commands

The repository now provides a small `Makefile`:

```bash
make test
make test-fast
make verify-fast
```

Notes:

- `make test-fast` defaults to `TEST_PARALLEL=4`
- override the worker count with `make test-fast TEST_PARALLEL=2`
- `make verify-fast` runs static compilation, Django checks, deploy checks, and the fast parallel suite

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
