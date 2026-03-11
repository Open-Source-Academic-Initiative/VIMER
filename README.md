# VIMER

This is the authoritative project document. This `README.md` consolidates VIMER's functional, technical, and operational documentation.

## Summary

VIMER is a Django MVP designed to connect demand-side and supply-side organizations around R&D&I challenges.

Current status:
- Working development baseline.
- Main flow implemented: signup, login, challenge listing, challenge detail, challenge publishing, and application submission.
- Write-side use cases now run through explicit application services in `identity` and `marketplace`.
- Application duplication is enforced with an explicit database constraint.
- The automated test suite currently passes with 8 tests.
- Not production-ready yet: security hardening, broader test coverage, and several operational gaps still need to be closed.

## Domain

VIMER models three core concepts:
- `Organization`: a legal entity with a single market role, either `DEMAND_SIDE` or `SUPPLY_SIDE`.
- `Challenge`: an R&D&I challenge or need published by a demand-side organization.
- `Application`: a technical proposal submitted by a supply-side organization to a challenge.

Ubiquitous language:
- Demand-side organization: publishes challenges.
- Supply-side organization: submits solutions.
- Representative: a human user operating on behalf of an organization.

## Architecture

The project follows a simple app-based split:

```text
config/           Django configuration
apps/identity/    Custom user, signup, and authentication
apps/corporate/   Organizations and market roles
apps/marketplace/ Challenges and applications
templates/        HTML templates
```

Use cases are orchestrated through explicit application services instead of embedding write-side workflow logic directly inside Django forms or generic ORM-backed views.

Write-side application layer:

```text
apps/identity/application/     Registration command, exceptions, and service
apps/marketplace/application/  Challenge publication and application services
```

Main models:
- `identity.User`: extends `AbstractUser` and links to `corporate.Organization`.
- `corporate.Organization`: stores tax ID, legal name, market role, and contact data.
- `marketplace.Challenge`: a challenge published by a demand-side organization.
- `marketplace.Application`: a solution proposal submitted by a supply-side organization.

## Implemented functionality

- Unified user and organization signup.
- Login and logout.
- Marketplace access restricted to authenticated users.
- Role-aware navigation.
- Challenge publishing by demand-side organizations.
- Challenge applications by supply-side organizations.
- Basic Django admin integration.
- Basic containerization with `Dockerfile` and `docker-compose.yml`.

## Current business rules

- An organization's tax ID must be unique.
- Only `DEMAND_SIDE` organizations can publish challenges.
- Only `SUPPLY_SIDE` organizations can apply to challenges.
- An organization cannot apply twice to the same challenge.

Duplicate challenge applications are enforced both in domain validation and through an explicit `UniqueConstraint` at the database level. Role restrictions are still enforced mainly through application logic and model validation.

## Actual project state

Strengths:
- The project starts correctly and `python manage.py check` reports no errors.
- `python manage.py test` currently passes with 8 tests.
- The repository is structured and the current branch is `foundation`.
- The core domain is already modeled and navigable.
- The write side is now routed through explicit application services instead of form-bound persistence logic.

Current limitations:
- The default profile is still development-oriented.
- Deployment security still depends on correct environment configuration.
- Test coverage is still limited.
- SQLite is still the default database.

## Fixes applied during this consolidation

Priority issues identified during the audit were fixed:
- Added the missing challenge creation template.
- Changed logout to use `POST`, avoiding the previous `405` from a `GET` link.
- Passed the selected challenge into the application form context.
- Signup now collects and stores `contact_phone`, aligned with the model.
- Added `ASGI_APPLICATION`.
- `ALLOWED_HOSTS` now has a safe local default compatible with tests (`localhost`, `127.0.0.1`, `[::1]`, `testserver`).
- Added explicit application services for registration, challenge publication, and proposal submission.
- Replaced `unique_together` on applications with an explicit `UniqueConstraint`.
- Expanded automated coverage to 8 tests, including application-service behavior.

## Main routes

- `/signup/`: user and organization signup
- `/login/`: login
- `/logout/`: logout via `POST`
- `/marketplace/`: challenge list
- `/marketplace/challenge/create/`: challenge creation
- `/marketplace/challenge/<id>/`: challenge detail
- `/marketplace/challenge/<id>/apply/`: proposal submission
- `/admin/`: administration

## Requirements

- Python 3.12+
- Django 6.0.x
- Pillow
- django-environ

Dependencies are defined in [requirements.txt](requirements.txt).

## Local setup

1. Create a virtual environment and install dependencies.
2. Define `.env` if explicit values are needed.
3. Run migrations.
4. Create a superuser if needed.
5. Start the server.

Commands:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Relevant environment variables:
- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `CSRF_TRUSTED_ORIGINS`

Environment behavior:
- Development: `DEBUG=True`, SQLite by default, secure cookies disabled, and local `ALLOWED_HOSTS` automatically included.
- Production: requires `SECRET_KEY`, allows an external `DATABASE_URL`, and enables HSTS, secure cookies, and HTTPS redirect by default unless explicitly overridden by environment configuration.

## Docker

The project includes:
- `Dockerfile`
- `docker-compose.yml`

Both currently use `runserver`, so they are suitable for development, not production.

## Verification

Useful commands:

```bash
python manage.py check
python manage.py check --deploy
python manage.py test
```

## Priority backlog

- Harden production configuration (`DEBUG=False`, secure cookies, HSTS, SSL redirect).
- Move to a real production server and deployment stack.
- Add more tests for permissions, validations, and business-rule failures.
- Evaluate additional database constraints to reinforce remaining domain invariants.
- Improve form and template UX.
- Define a persistence and deployment strategy beyond SQLite.

## Documentation notes

This file replaces the previous scattered status documents as the main project reference. The auxiliary Markdown files about Django 6.0 are local reference notes and are not part of VIMER's functional documentation.
