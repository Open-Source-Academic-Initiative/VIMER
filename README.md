# VIMER

This is the authoritative project document. This `README.md` consolidates VIMER's functional, technical, and operational documentation.

## Summary

VIMER is a Django MVP designed to connect organizations acting as `Solicitantes` with organizations acting as `Proveedores tecnológicos` around R&D&I challenges.

Current status:
- Stable development baseline.
- A public landing page is available at `/`.
- The main flow is implemented: signup, login, challenge listing, challenge detail, challenge publishing, and application submission.
- Write-side use cases are routed through explicit application services in `identity` and `marketplace`.
- Duplicate applications are prevented through an explicit database constraint.
- The application submission flow now distinguishes duplicate applications from other business-rule validation errors.
- The automated test suite currently passes with 20 tests.
- Django Admin now prevents a platform superuser from deleting its own account.
- The project is not production-ready yet: security hardening, broader test coverage, and several operational gaps still need to be addressed.

## Domain

VIMER models three core concepts:
- `Organization`: a legal entity with a single market role, either `DEMAND_SIDE` (`Solicitante`) or `SUPPLY_SIDE` (`Proveedor tecnológico`).
- `Challenge`: an R&D&I challenge or need published by a `Solicitante` organization.
- `Application`: a technical proposal submitted by a `Proveedor tecnológico` organization in response to a challenge.

Ubiquitous language:
- `Solicitante` organization: publishes challenges.
- `Proveedor tecnológico` organization: submits solutions.
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
- `marketplace.Challenge`: a challenge published by a `Solicitante` organization.
- `marketplace.Application`: a solution proposal submitted by a `Proveedor tecnológico` organization.

## Implemented functionality

- Public landing page for unauthenticated visitors.
- Unified user and organization signup.
- Login and logout.
- Marketplace access restricted to authenticated users.
- Role-aware navigation.
- Challenge publishing by `Solicitante` organizations.
- Challenge applications by `Proveedor tecnológico` organizations.
- Basic Django admin integration.
- Platform superuser safeguard against self-deletion in Django Admin.
- Basic containerization with `Dockerfile` and `docker-compose.yml`.

## Current business rules

- An organization's tax ID must be unique.
- Only `DEMAND_SIDE` (`Solicitante`) organizations can publish challenges.
- Only `SUPPLY_SIDE` (`Proveedor tecnológico`) organizations can apply to challenges.
- An organization cannot apply twice to the same challenge.
- A platform superuser cannot delete its own account from Django Admin.

Duplicate applications are enforced both through domain validation and through an explicit `UniqueConstraint` at the database level. Role restrictions are still enforced primarily through application logic and model validation.

## Current Project State

Strengths:
- The project starts correctly and `python manage.py check` reports no errors.
- `python manage.py test` currently passes with 20 tests.
- The repository is well structured, and the current active local iteration branch is `baseline-iteration`.
- The core domain is already modeled and navigable.
- The write side is now routed through explicit application services instead of form-bound persistence logic.
- The root route now exposes a dedicated landing page instead of sending users directly to signup.
- The admin now includes an explicit safeguard to prevent a superuser from deleting its own account.

Current limitations:
- The default runtime profile remains development-oriented unless environment variables are configured carefully.
- Deployment security still depends on correct environment configuration.
- Test coverage is still limited.
- SQLite is still the default database.
- `README.md` should be kept in sync as the local iteration evolves, since some operational details change faster than the core architecture.

## Fixes applied during this consolidation

Priority issues identified during the audit were fixed:
- Added the missing challenge creation template.
- Changed logout to use `POST`, avoiding the previous `405` from a `GET` link.
- Passed the selected challenge into the application form context.
- Signup now collects and stores `contact_phone`, in alignment with the model.
- Added `ASGI_APPLICATION`.
- `ALLOWED_HOSTS` now has a safe local default compatible with tests (`localhost`, `127.0.0.1`, `[::1]`, `testserver`).
- Added explicit application services for registration, challenge publication, and proposal submission.
- Replaced `unique_together` on applications with an explicit `UniqueConstraint`.
- Corrected application-submission error handling so duplicate applications are no longer confused with other validation failures.
- Added a public landing page at `/` to separate public navigation from the signup flow.
- Added an admin safeguard so a superuser cannot delete its own account.
- Expanded automated coverage to 20 tests, including duplicate username/email handling, registration-service validation errors, and superuser self-deletion safeguards.

## Main routes

- `/`: public landing page
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
2. Create a `.env` file if explicit values are needed.
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
- Development: `DEBUG=True`, SQLite by default, secure cookies disabled, and local `ALLOWED_HOSTS` entries automatically included.
- Production: requires `SECRET_KEY`, supports an external `DATABASE_URL`, and enables HSTS, secure cookies, and HTTPS redirects by default unless explicitly overridden by environment configuration.

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

Note:
- In this workspace, running tests with `DEBUG=True` avoids HTTPS redirects caused by stricter local `.env` settings.

## Priority backlog

- Keep this README synchronized with the current implementation and local branch reality.
- Harden production configuration (`DEBUG=False`, secure cookies, HSTS, SSL redirect).
- Move to a real production server and deployment stack.
- Add more tests for permissions, validations, and business-rule failures.
- Evaluate additional database constraints to reinforce remaining domain invariants.
- Improve form and template UX.
- Define a persistence and deployment strategy beyond SQLite.

## Documentation notes

This file is the versioned, authoritative project reference. Local state snapshots such as `status_de_desarrollo.md` and `resumen_ejecutivo.md` may exist as ignored workspace notes, while `django_skill.md` and `django-report.md` are Django 6.0 reference notes rather than VIMER functional documentation.
