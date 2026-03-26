# VIMER

This is the authoritative project document. This `README.md` consolidates VIMER's functional, technical, and operational documentation.

## Summary

VIMER is a Django MVP designed to connect organizations acting as `Solicitantes` with organizations acting as `Proveedores tecnológicos` around R&D&I challenges.

Current status:
- Stable development baseline.
- A public landing page is available at `/`.
- The main flow is implemented: signup, login, challenge listing, challenge detail, challenge publishing, and application submission.
- Write-side use cases are routed through explicit application services in `identity`, `marketplace`, `evaluation`, and `notifications`.
- Duplicate applications are prevented through an explicit database constraint.
- The application submission flow now distinguishes duplicate applications from other business-rule validation errors.
- The automated test suite currently passes with 93 tests.
- Django Admin now prevents a platform superuser from deleting its own account.
- Organizations can upload a custom logo during signup, limited to PNG/JPG; otherwise a procedural default avatar is generated automatically.
- Organization logos/avatars are visible in marketplace publications and proposal listings.
- Marketplace invariants for role enforcement and duplicate applications are now expressed through explicit domain rule modules.
- Challenges now expose an explicit lifecycle status and optional application deadline.
- Challenges now capture explicit evaluation criteria, required before evaluation can start.
- Challenges now persist those evaluation criteria as structured entries that can be reused in evaluation flows.
- Evaluation now supports criterion-by-criterion assessments for each proposal before final adjudication.
- Evaluation now supports multiple designated evaluators contributing independently to the same proposal criterion.
- Publisher-facing challenge and adjudication views now expose aggregated evaluation summaries per proposal.
- Publisher-facing evaluation flows now expose an explicit comparative ranking between proposals based on completed criterion assessments.
- Applications are accepted only while a challenge is published and still open for submission.
- Proposals now use structured required components instead of relying only on a single free-text field.
- Submitted proposals are immutable after submission.
- The evaluation context is now explicit and supports adjudication with a mandatory decision comment.
- Evaluation outcomes now emit explicit domain events after transaction commit.
- Challenge detail for publishers now includes an evaluation history timeline built from those domain events.
- A new internal notifications context now consumes evaluation events and exposes an in-app inbox with unread counts.
- Award decisions now persist a snapshot of the winning proposal's evaluation state for later traceability.
- Criterion-by-criterion proposal evaluation now emits its own domain event, feeding timeline and applicant notifications.
- Proposal-evaluation activity now also notifies the evaluation team and enriches publisher-facing audit views.
- The local test suite now ignores the workspace `.env` by default, reducing environment-specific failures.
- The heaviest test modules now reuse immutable fixtures through `setUpTestData()`, reducing suite runtime sharply without weakening isolation.
- A repository-level `Makefile` now exposes `make test-fast` and `make verify-fast` for the optimized validation path.
- Containerized serving now uses `gunicorn` instead of Django's development server.
- Challenges now support a formal evaluation team with designated evaluators, one designated adjudicator, and optional observers.
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

Versioned domain references:
- `docs/domain/ontology_v4.md`: canonical ontology
- `docs/domain/glossary.md`: preferred business language
- `docs/domain/context_map.md`: bounded-context view
- `docs/domain/invariants.md`: traceable rule inventory
- `docs/project_diagrams.md`: current functional-flow and architecture diagrams
- `docs/testing_strategy.md`: current automated-validation and test-optimization guidance

## Architecture

The project follows a simple app-based split:

```text
config/           Django configuration
apps/identity/    Custom user, signup, and authentication
apps/corporate/   Organizations and market roles
apps/marketplace/ Challenges and applications
apps/evaluation/  Adjudication and evaluation history
apps/notifications/ Internal notifications and inbox
templates/        HTML templates
```

Use cases are orchestrated through explicit application services instead of embedding write-side workflow logic directly inside Django forms or generic ORM-backed views.

Write-side application layer:

```text
apps/identity/application/     Registration command, exceptions, and service
apps/marketplace/application/  Challenge publication and application services
apps/evaluation/application/   Evaluation-team, scoring, and adjudication services
apps/notifications/application/ Notification read-state service
```

Main models:
- `identity.User`: extends `AbstractUser` and links to `corporate.Organization`.
- `corporate.Organization`: stores tax ID, legal name, market role, and contact data.
- `marketplace.Challenge`: a challenge published by a `Solicitante` organization.
- `marketplace.Application`: a solution proposal submitted by a `Proveedor tecnológico` organization.
- `evaluation.AwardDecision`: adjudication outcome for a challenge.
- `notifications.Notification`: in-app notification delivered to a representative.

## Implemented functionality

- Public landing page for unauthenticated visitors.
- Unified user and organization signup.
- Optional organization logo upload at signup, with procedural default avatar generation.
- Organization logos/avatars rendered in challenge listings, challenge detail pages, and visible proposal entries.
- Login and logout.
- Marketplace access restricted to authenticated users.
- Role-aware navigation.
- Challenge publishing by `Solicitante` organizations.
- Challenge lifecycle state and optional application deadline.
- Challenge evaluation criteria captured at publication time.
- Structured evaluation-criteria entries derived from challenge publication.
- Challenge applications by `Proveedor tecnológico` organizations.
- Structured proposal submission with required components.
- Evaluation and adjudication flow for challenge publishers.
- Evaluation team management with designated evaluators, adjudicator, and observers.
- Criterion-by-criterion proposal evaluation during `UNDER_EVALUATION`.
- Blind evaluation and adjudication views that hide applicant identity until award.
- Aggregated evaluation summaries per proposal, including coverage, registered assessment count, average score, and criterion detail.
- Explicit comparative proposal ranking in publisher-facing evaluation and adjudication views.
- Multiple independent evaluator assessments per criterion, with one current persisted assessment per `(proposal, criterion, evaluator)`.
- Persisted evaluation snapshot on award decisions, including ranking and score context.
- Evaluation history timeline for challenge publishers.
- Internal notifications inbox with unread counter and mark-all-read flow.
- Proposal-evaluation notifications for applicant organizations after scoring is registered.
- Proposal-evaluation activity notifications for the evaluation team.
- Test execution isolated by default from local `.env` overrides.
- Basic Django admin integration.
- Platform superuser safeguard against self-deletion in Django Admin.
- Containerized serving with `gunicorn` in `Dockerfile` and `docker-compose.yml`.

## Current business rules

- An organization's tax ID must be unique.
- Only `DEMAND_SIDE` (`Solicitante`) organizations can publish challenges.
- Only `SUPPLY_SIDE` (`Proveedor tecnológico`) organizations can apply to challenges.
- Challenges only accept applications while they remain published and open for submission.
- A challenge must define evaluation criteria before it can move into evaluation.
- A winning proposal becomes eligible for adjudication once each criterion has at least one registered assessment.
- Only the publisher organization can manage and execute evaluation operations for its challenge.
- Evaluation roles can only be assigned to members of the publisher organization.
- At least one designated evaluator and one designated adjudicator are required before evaluation can start.
- Only designated evaluators can score proposals.
- Only the designated adjudicator can adjudicate.
- A designated evaluator keeps only one current assessment per `(proposal, criterion, evaluator)`; rescoring updates that evaluator's current assessment.
- An organization cannot apply twice to the same challenge.
- A submitted proposal must include all required structured components.
- A submitted proposal cannot be modified after submission.
- A challenge can have at most one adjudicated winning proposal.
- A platform superuser cannot delete its own account from Django Admin.
- Organization logos uploaded at signup are limited to PNG/JPG; when no custom image is provided, a procedural PNG avatar is generated automatically.

Duplicate applications are enforced both through domain validation and through an explicit `UniqueConstraint` at the database level. Role restrictions are still enforced primarily through application logic and model validation.

## Current Project State

Strengths:
- The project starts correctly and `python manage.py check` reports no errors.
- `python manage.py test` currently passes with 93 tests.
- The repository is well structured, and the current active local iteration branch is `baseline-iteration`.
- The core domain is already modeled and navigable.
- The write side is now routed through explicit application services instead of form-bound persistence logic.
- The root route now exposes a dedicated landing page instead of sending users directly to signup.
- The admin now includes an explicit safeguard to prevent a superuser from deleting its own account.
- Signup now supports custom organization logos and guarantees a default procedural avatar when no image is uploaded.
- Marketplace publications now display the publisher or applicant organization logo/avatar where relevant.
- Challenges now carry an explicit lifecycle state and optional application deadline.
- Challenges now store explicit evaluation criteria and expose them in publication/detail flows.
- Challenges now materialize structured evaluation-criteria entries, including migration backfill for existing text-based criteria.
- Applications now store structured proposal components and enforce immutability after submission.
- Evaluation now lives in its own Django app and closes the loop through criterion assessment plus adjudication.
- Evaluation views now provide an explicit proposal ranking plus multi-evaluator assessment detail to support adjudication decisions.
- Award decisions now keep an evaluation snapshot so adjudication remains auditable after later UI changes.
- Evaluation event consumers now also react to proposal scoring with timeline projections, applicant notifications, and evaluation-team notifications.
- Evaluation permissions now follow formal designated roles instead of any publisher member being able to mutate the process.
- The test runner is now isolated from local `.env` overrides unless explicitly requested.
- Test setup for the heaviest suites now reuses shared immutable fixtures through `setUpTestData()`, substantially reducing database setup overhead.
- Notifications now live in their own Django app and consume evaluation domain events.

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
- Added optional signup logo upload with strict PNG/JPG validation and procedural PNG avatar generation as fallback.
- Introduced explicit marketplace domain rule modules to name and centralize the current publication/application invariants.
- Added challenge lifecycle semantics with explicit status and optional application deadline.
- Added explicit evaluation criteria on challenges and required them before a challenge can enter evaluation.
- Added structured evaluation-criteria entries for challenges and backfilled them from existing text criteria.
- Added criterion-by-criterion proposal assessments and required criterion coverage before adjudicating a winning proposal.
- Added reusable evaluation summaries so publishers can compare proposals during review and adjudication.
- Added explicit comparative proposal ranking in evaluation and adjudication views, prioritizing criterion coverage, stronger averages, and richer assessment volume.
- Added persisted adjudication snapshots with ranking, score, evaluation-completeness, and assessment-count context for the winning proposal.
- Added explicit proposal-evaluation events with timeline persistence and applicant-facing notifications.
- Evolved proposal assessment from a single-evaluator model to multiple independent evaluators per criterion, with aggregate scoring across all registered assessments.
- Added evaluation-team notifications and richer publisher-facing audit detail when proposal-scoring activity is recorded.
- Isolated test settings from the local `.env` by default through `READ_DOT_ENV_FILE`.
- Switched containerized serving from `runserver` to `gunicorn`.
- Added formal evaluation-role assignments with designated evaluators, a designated adjudicator, observer roles, UI management, and permission enforcement.
- Optimized the heaviest test modules to reuse immutable fixtures via `setUpTestData()` and documented a standard fast-validation path through `make test-fast`.
- Prevented applications against challenges that are closed or no longer open for submission.
- Formalized proposal submission with structured required components and immutable submitted applications.
- Added an explicit evaluation context with challenge transition to evaluation, adjudication, mandatory comment, and one winning proposal per challenge.
- Added an internal notifications context with event-driven inbox entries, unread counts, and mark-all-read behavior.
- Expanded automated coverage to 93 tests, including duplicate username/email handling, registration-service validation errors, image-format validation, avatar generation, marketplace logo rendering, superuser self-deletion safeguards, negative flow/service tests for marketplace role restrictions, challenge lifecycle enforcement, proposal completeness, post-submission immutability, evaluation/adjudication flows, evaluation domain-event emission after commit, event-driven evaluation history persistence/rendering, internal notification delivery/read-state flows, evaluation-criteria enforcement in publication/evaluation flows, structured evaluation-criteria rendering/persistence, criterion-assessment enforcement before adjudication, publisher-facing evaluation summary rendering, adjudication snapshots, proposal-evaluation events, formal evaluation-role enforcement, challenge-detail isolation of publisher-only evaluation read models, blind evaluation/adjudication identity protection until award, multiple-evaluator aggregation/update semantics, draft-visibility regressions, model-level logo validation, and structured-criteria reconciliation.

## Main routes

- `/`: public landing page
- `/signup/`: user and organization signup
- `/login/`: login
- `/logout/`: logout via `POST`
- `/marketplace/`: challenge list
- `/marketplace/challenge/create/`: challenge creation
- `/marketplace/challenge/<id>/`: challenge detail
- `/marketplace/challenge/<id>/apply/`: proposal submission
- `/evaluation/challenge/<id>/start/`: start challenge evaluation
- `/evaluation/challenge/<id>/roles/`: manage evaluation team
- `/evaluation/challenge/<id>/application/<application_id>/evaluate/`: evaluate a proposal by criterion
- `/evaluation/challenge/<id>/award/`: register adjudication decision
- `/notifications/`: notifications inbox
- `/notifications/mark-all-read/`: mark all notifications as read
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
- `TEST_DEBUG`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `CSRF_TRUSTED_ORIGINS`
- `READ_DOT_ENV_FILE`

Environment behavior:
- Development: `DEBUG=True`, SQLite by default, secure cookies disabled, and local `ALLOWED_HOSTS` entries automatically included.
- Production: requires `SECRET_KEY`, supports an external `DATABASE_URL`, and enables HSTS, secure cookies, and HTTPS redirects by default unless explicitly overridden by environment configuration.
- Tests: ignore the local `.env` by default and use a test-oriented debug profile unless you intentionally override it with `TEST_DEBUG` or `READ_DOT_ENV_FILE=True`.

## Docker

The project includes:
- `Dockerfile`
- `docker-compose.yml`

Both now use `gunicorn` as the application server. This improves the serving strategy, but the stack still is not a full production deployment by itself.

## Verification

Useful commands:

```bash
python manage.py check
python manage.py check --deploy
python manage.py test
```

Optimized local validation path:

```bash
make test-fast
make verify-fast
make test-fast TEST_PARALLEL=2
```

Current measured suite timings after the fixture optimization:

- `python manage.py test`: `56.357s` test runtime (`58.91s` wall clock)
- `python manage.py test --parallel 2`: `32.090s` test runtime (`34.68s` wall clock)
- `python manage.py test --parallel 4`: `30.723s` test runtime (`33.63s` wall clock)

The previous full-suite baseline before the optimization pass was `396.022s`.

## Priority backlog

- Keep this README synchronized with the current implementation and local branch reality.
- Harden production configuration (`DEBUG=False`, secure cookies, HSTS, SSL redirect).
- Complete the production deployment stack around `gunicorn` and external infrastructure.
- Add more tests for permissions, validations, and business-rule failures.
- Evaluate additional database constraints to reinforce remaining domain invariants.
- Improve form and template UX.
- Define a persistence and deployment strategy beyond SQLite.

## Documentation notes

This file is the versioned, authoritative project reference. Local state snapshots such as `status_de_desarrollo.md` and `resumen_ejecutivo.md` may exist as ignored workspace notes, while `django_skill.md` and `django-report.md` are Django 6.0 reference notes rather than VIMER functional documentation.
