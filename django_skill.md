---
name: django-expert
version: 6.0
description: >
  Complete Django 6.0 knowledge skill for use in AI CLIs (Claude, Gemini, Codex).
  Enables expert-level Django assistance including architecture, ORM, views,
  security, testing, deployment, and official contrib modules.
author: generated
license: open
---

# Django 6.0 — Complete Knowledge Skill

> Coverage note:
> This skill is designed as a dense operational reference for Django 6.0 based on the official documentation set, especially the release notes, topic guides, how-to guides, API reference, and contrib reference. It is intentionally optimized for code-generation agents and fast technical lookup.
>
> ⚠️ Exhaustive page-by-page verification of every single reachable documentation page was not mechanically guaranteed in the runtime used to build this file. When a behavior is version-sensitive, prefer the APIs and semantics explicitly called out in Django 6.0 release notes and reference pages.
>
> 💡 Use this file as a drop-in system prompt, project memory file, or context pack for Codex, Claude Code, Gemini CLI, or Copilot.

## How to use this skill

- Assume **Django 6.0** and **Python 3.12–3.14** unless the user explicitly states otherwise.
- Prefer official, documented APIs over project folklore.
- Prefer explicit, conservative code over clever abstractions.
- When the task touches security, migrations, transactions, caching, async, or deployment, surface trade-offs before writing code.
- When code generation depends on undocumented project conventions, ask for those conventions or use Django defaults.

---

## 1. Core Philosophy & Architecture

Django is a batteries-included Python web framework built around explicit configuration, reusable apps, stable APIs, and a strong split between URL dispatch, view orchestration, data modeling, and presentation. The core mental model is: **HTTP enters through URL routing, orchestration happens in views/middleware, persistence happens through the ORM, rendering happens via templates or serializers, and cross-cutting behavior lives in middleware/settings**. Django favors convention, but almost every major subsystem is replaceable or extensible.

### Key architecture primitives

| Layer | Main objects | Responsibility |
|---|---|---|
| Configuration | `settings.py`, `django.setup()` | Load settings, app registry, logging, global runtime |
| App registry | `AppConfig`, `apps` | App metadata, startup hooks, model lookup |
| HTTP ingress | ASGI/WSGI handler, middleware | Request normalization, cross-cutting concerns |
| Routing | `path()`, `re_path()`, `include()` | Map URL patterns to views |
| Views | FBVs, CBVs | Orchestrate request/response logic |
| ORM | `Model`, `Manager`, `QuerySet` | Persistence, querying, transactions |
| Templates | DTL backend, template loaders | HTML generation and presentation logic |
| Forms | `Form`, `ModelForm`, formsets | Validation, HTML form rendering, cleaning |
| Contrib | `auth`, `admin`, `sessions`, etc. | Higher-level built-in features |

### Core API surface

- `django.setup(set_prefix=True)`
- `django.apps.AppConfig`
- `django.conf.settings`
- `django.urls.path(route, view, kwargs=None, name=None)`
- `django.urls.re_path(route, view, kwargs=None, name=None)`
- `django.urls.include(module, namespace=None)`
- `django.http.HttpRequest`
- `django.http.HttpResponse`
- `django.db.models.Model`

### Canonical example

```python
# mysite/settings.py
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "blog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
```

```python
# blog/apps.py
from django.apps import AppConfig

class BlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "blog"
```

> 💡 Treat each app as a bounded feature module with models, views, templates, tests, admin, and URLs. Avoid “god apps”.

### Important settings

- `INSTALLED_APPS`
- `MIDDLEWARE`
- `ROOT_URLCONF`
- `TEMPLATES`
- `DATABASES`
- `STORAGES`
- `DEFAULT_AUTO_FIELD`
- `USE_TZ`
- `LANGUAGE_CODE`
- `TIME_ZONE`

### Common mistakes

> ⚠️ Putting too much startup logic in `AppConfig.ready()` can create import loops or duplicate side effects in management commands and test runs.

> ⚠️ Importing models at module import time from unpredictable places often causes circular dependencies; prefer lazy lookups, app registry lookup, or local imports.

### Version-specific notes

- Django 6.0 officially supports Python 3.12, 3.13, and 3.14.
- Django 6.0 adds first-party CSP support, template partials, and the Tasks framework.

### Cross-references

- See [2. Project Setup & Configuration](#2-project-setup--configuration)
- See [10. Middleware](#10-middleware)
- See [16. Async & ASGI](#16-async--asgi)

---

## 2. Project Setup & Configuration

A Django project is the deployment/configuration shell; apps are reusable feature modules inside it. The setup path is typically: create venv, install Django, create project, create app, configure settings, migrate database, register URLs, then run the server.

### Minimal bootstrap flow

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install "Django>=6.0,<6.1"
django-admin startproject mysite .
python manage.py startapp blog
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Key files

| File | Purpose |
|---|---|
| `manage.py` | Project-local CLI entrypoint |
| `mysite/settings.py` | Runtime configuration |
| `mysite/urls.py` | Root URL configuration |
| `mysite/asgi.py` | ASGI entrypoint |
| `mysite/wsgi.py` | WSGI entrypoint |
| `blog/models.py` | ORM models |
| `blog/views.py` | Views |
| `blog/admin.py` | Admin registrations |
| `blog/tests.py` | Tests |

### Core API surface

- `django-admin startproject`
- `django-admin startapp`
- `manage.py migrate`
- `manage.py makemigrations`
- `manage.py check`
- `manage.py diffsettings`
- `manage.py shell`

### Canonical configuration skeleton

```python
# mysite/settings.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "replace-me"
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "blog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "mysite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "mysite.wsgi.application"
ASGI_APPLICATION = "mysite.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

### High-value settings reference

| Setting | Why it matters |
|---|---|
| `SECRET_KEY` | Signing, tokens, cookies, cryptographic integrity |
| `SECRET_KEY_FALLBACKS` | Key rotation without instant invalidation |
| `DEBUG` | Security/performance toggle; never enable in production |
| `ALLOWED_HOSTS` | Host header validation |
| `DATABASES` | DB engines, credentials, transactions |
| `TEMPLATES` | Loaders, context processors, backend behavior |
| `STORAGES` | Static/media storage backends |
| `DEFAULT_AUTO_FIELD` | Default PK type for new models |
| `CSRF_TRUSTED_ORIGINS` | Reverse proxy / cross-origin safe POST scenarios |
| `SECURE_*` settings | HTTPS hardening, HSTS, CSP, redirects |

### Common mistakes

> ⚠️ Leaving `SECRET_KEY` static across environments makes rotation and incident response harder.

> ⚠️ Using `DEBUG=True` in any public environment leaks diagnostics and changes behavior.

> ⚠️ Setting `ALLOWED_HOSTS = ["*"]` in production removes a meaningful protection layer.

### Version-specific notes

- In 6.0, CSP is configured with `SECURE_CSP` and `SECURE_CSP_REPORT_ONLY`.
- `SECRET_KEY_FALLBACKS` remains the correct rotation mechanism.
- `TASKS` is a new top-level setting in 6.0.

### Cross-references

- See [14. Security Best Practices](#14-security-best-practices)
- See [19. Settings — Complete Reference](#19-settings--complete-reference)
- See [20. Deployment](#20-deployment-wsgiasgi-checklist-production-config)

---

## 3. Models & ORM

The ORM maps Python classes to database tables and `QuerySet` operations to SQL. The mental model is: models define schema and behavior, managers define entry points, querysets define composable query expressions, and migrations transport schema change over time.

### 3.1 Field Types & Options

Fields encode database column type, validation behavior, form generation hints, serialization, defaults, indexing, and relationship semantics.

#### Common field types

| Field | Typical use |
|---|---|
| `CharField(max_length=...)` | Short text |
| `TextField()` | Long text |
| `IntegerField()` / `BigIntegerField()` | Integer values |
| `BooleanField()` | True/False |
| `DateField()` / `DateTimeField()` | Date/time |
| `DecimalField(max_digits=..., decimal_places=...)` | Money, exact decimals |
| `FloatField()` | Approximate decimals |
| `UUIDField()` | UUID identity |
| `JSONField()` | Structured JSON |
| `EmailField()` / `URLField()` | Typed string + validation |
| `FileField()` / `ImageField()` | File references |
| `ForeignKey()` / `ManyToManyField()` / `OneToOneField()` | Relationships |

#### Field options

| Option | Effect |
|---|---|
| `null=True` | Database NULL allowed |
| `blank=True` | Validation/form empty allowed |
| `default=...` | Python-side default |
| `db_default=...` | Database-side default |
| `unique=True` | Unique constraint |
| `db_index=True` | DB index |
| `choices=...` | Constrained value set |
| `verbose_name=...` | Human-readable label |
| `help_text=...` | Form/admin hint |
| `editable=False` | Omit from ModelForm/admin by default |

> 💡 `blank` is validation-level; `null` is storage-level. They are not interchangeable.

#### Canonical example

```python
from django.db import models
from django.utils import timezone

class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True)
    body = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self) -> str:
        return self.title
```

#### Gotchas

> ⚠️ `default={}` on mutable types is wrong. Use `default=dict` or `default=list`.

> ⚠️ `auto_now` and `auto_now_add` are convenient but inflexible; explicit timestamps are usually easier to reason about.

#### Version-specific notes

- `db_default` is the right tool when the database itself must own the default.
- Composite primary keys are supported in 6.0 via `CompositePrimaryKey`, but were introduced in 5.2.

### 3.2 QuerySets & Managers

A `Manager` is the table-level entry point (`Model.objects`), while a `QuerySet` is a lazy, chainable SQL builder. QuerySets are immutable in practice: each refinement returns a new queryset.

#### Key API surface

- `Model.objects.all()`
- `filter(*args, **kwargs)`
- `exclude(*args, **kwargs)`
- `get(*args, **kwargs)`
- `create(**kwargs)`
- `bulk_create(objs, batch_size=None, ignore_conflicts=False, update_conflicts=False, ...)`
- `update(**kwargs)`
- `delete()`
- `select_related(*fields)`
- `prefetch_related(*lookups)`
- `annotate(*args, **kwargs)`
- `aggregate(*args, **kwargs)`
- `values(*fields, **expressions)`
- `values_list(*fields, flat=False, named=False)`
- `order_by(*fields)`
- `distinct(*fields)`
- `exists()`
- `count()`
- `iterator(chunk_size=None)`
- async variants for DB-triggering methods where provided, typically prefixed with `a...`

#### Canonical example

```python
from django.db import models
from django.db.models import Count, Q

class PublishedArticleQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Article.Status.PUBLISHED)

    def with_comment_count(self):
        return self.annotate(comment_count=Count("comments"))

class ArticleManager(models.Manager):
    def get_queryset(self):
        return PublishedArticleQuerySet(self.model, using=self._db)

    def published(self):
        return self.get_queryset().published()

class Article(models.Model):
    # fields omitted for brevity
    objects = models.Manager()
    published_objects = ArticleManager()
```

#### Custom manager guidance

- Put filtering rules that always matter in a custom queryset.
- Expose those rules through a manager for ergonomic access.
- Avoid hiding records globally unless you fully understand admin, migrations, tests, and maintenance implications.

#### Gotchas

> ⚠️ Never assume queryset evaluation is free. It triggers on iteration, slicing patterns, casting to `list()`, `len()`, `bool()`, template rendering, and many helper methods.

> ⚠️ `select_related()` follows single-valued relations; `prefetch_related()` is for many-valued or custom-prefetched relations.

### 3.3 Relationships (FK, M2M, O2O)

Relationships are model-level declarations that become foreign keys, join tables, or unique one-to-one links in the DB. Django expresses reverse relations automatically.

#### Core API surface

- `models.ForeignKey(to, on_delete, related_name=None, related_query_name=None, null=False, blank=False, db_index=True, ...)`
- `models.ManyToManyField(to, related_name=None, through=None, symmetrical=True, blank=False, ...)`
- `models.OneToOneField(to, on_delete, parent_link=False, ...)`

#### Canonical example

```python
class Author(models.Model):
    name = models.CharField(max_length=200)

class Profile(models.Model):
    author = models.OneToOneField(
        Author,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.TextField(blank=True)

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

class Article(models.Model):
    author = models.ForeignKey(
        Author,
        on_delete=models.PROTECT,
        related_name="articles",
    )
    tags = models.ManyToManyField(Tag, related_name="articles", blank=True)
```

#### `on_delete` choices

| Option | Meaning |
|---|---|
| `CASCADE` | Delete dependents |
| `PROTECT` | Block deletion |
| `RESTRICT` | Restrict with dependency-aware semantics |
| `SET_NULL` | Set FK to NULL |
| `SET_DEFAULT` | Set FK to field default |
| `SET(value)` | Set to custom value |
| `DO_NOTHING` | DB must handle it |

#### Gotchas

> ⚠️ `ManyToManyField` is unavailable until the instance has a primary key.

> ⚠️ Reverse relation names collide easily; set `related_name` deliberately in reusable apps.

### 3.4 Migrations

Migrations are the schema evolution layer. Django compares model state to migration state, produces operations, and applies them incrementally.

#### Main commands

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
python manage.py sqlmigrate app_label migration_name
```

#### Common migration operations

- `CreateModel`
- `DeleteModel`
- `AddField`
- `RemoveField`
- `AlterField`
- `RenameField`
- `RenameModel`
- `AddConstraint`
- `RemoveConstraint`
- `AddIndex`
- `RemoveIndex`
- `RunPython`
- `RunSQL`

#### Canonical data migration

```python
from django.db import migrations

def backfill_slugs(apps, schema_editor):
    Article = apps.get_model("blog", "Article")
    for article in Article.objects.filter(slug=""):
        article.slug = str(article.pk)
        article.save(update_fields=["slug"])

class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0004_add_slug"),
    ]

    operations = [
        migrations.RunPython(backfill_slugs, migrations.RunPython.noop),
    ]
```

#### Gotchas

> ⚠️ Never import live models directly inside migrations. Use `apps.get_model()`.

> ⚠️ Schema migrations and data migrations should be split when lock duration or rollback risk matters.

> ⚠️ Renames are better expressed as `RenameField`/`RenameModel` than delete-and-recreate patterns, to preserve data.

### 3.5 Signals

Signals are event hooks fired by Django internals or model lifecycle events. They are useful for cross-cutting reactions but easy to overuse.

#### Common built-in signals

- `pre_save`
- `post_save`
- `pre_delete`
- `post_delete`
- `m2m_changed`
- `pre_migrate`
- `post_migrate`
- `request_started`
- `request_finished`
- `got_request_exception`

#### Canonical example

```python
# blog/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Article

@receiver(post_save, sender=Article)
def notify_on_publish(sender, instance, created, **kwargs):
    if instance.status == Article.Status.PUBLISHED:
        # enqueue task, invalidate cache, etc.
        pass
```

```python
# blog/apps.py
from django.apps import AppConfig

class BlogConfig(AppConfig):
    name = "blog"

    def ready(self):
        import blog.signals  # noqa: F401
```

#### Gotchas

> ⚠️ Signals hide control flow. Prefer explicit service calls when the workflow is business-critical.

> ⚠️ Signal handlers that write to the same model can create recursion or duplicated work.

### Composite primary keys

Django 6.0 supports composite primary keys through `models.CompositePrimaryKey(...)`. This is powerful but still more constrained than single-column PKs and must be used intentionally.

```python
from django.db import models

class Membership(models.Model):
    pk = models.CompositePrimaryKey("user_id", "group_id")
    user_id = models.IntegerField()
    group_id = models.IntegerField()
    role = models.CharField(max_length=20)
```

> ⚠️ Composite PKs are virtual fields and do not behave exactly like normal scalar fields in all ORM/form contexts.

### Cross-references

- See [4. Views](#4-views)
- See [7. Forms & Validation](#7-forms--validation)
- See [15. Testing](#15-testing-unit-integration-client)

---

## 4. Views

Views orchestrate HTTP behavior: parse inputs, call domain logic, query models, render templates or return structured responses, and handle errors. Django supports both function-based views (FBVs) and class-based views (CBVs); the best choice depends on complexity, reuse needs, and team conventions.

### 4.1 Function-Based Views

FBVs are explicit, easy to trace, and usually the best choice for simple or irregular request flows.

#### Key API surface

- `HttpResponse(content="", status=200, content_type=None, headers=None)`
- `JsonResponse(data, encoder=DjangoJSONEncoder, safe=True, json_dumps_params=None, **kwargs)`
- `HttpResponseRedirect(redirect_to)`
- `redirect(to, *args, **kwargs)`
- `render(request, template_name, context=None, content_type=None, status=None, using=None)`
- `get_object_or_404(klass, *args, **kwargs)`
- `get_list_or_404(klass, *args, **kwargs)`
- `require_http_methods(request_method_list)`
- `require_GET`
- `require_POST`
- `csrf_exempt`, `csrf_protect`, `ensure_csrf_cookie`

#### Canonical example

```python
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, render
from .models import Article

def article_detail(request, slug):
    article = get_object_or_404(
        Article.objects.select_related("author"),
        slug=slug,
    )

    if article.status != Article.Status.PUBLISHED:
        raise Http404("Article not found")

    if request.headers.get("Accept") == "application/json":
        return JsonResponse(
            {
                "title": article.title,
                "slug": article.slug,
                "author": article.author.name,
            }
        )

    return render(request, "blog/article_detail.html", {"article": article})
```

#### Gotchas

> ⚠️ If a response varies by `Accept`, language, cookies, or auth-sensitive state, ensure caching is configured with matching `Vary` behavior.

### 4.2 Class-Based Views & Mixins

CBVs encode common request patterns as classes with override points. They work best when your flow matches Django’s lifecycle hooks.

#### Core CBV surface

- `View`
  - `setup(request, *args, **kwargs)`
  - `dispatch(request, *args, **kwargs)`
  - `http_method_not_allowed(request, *args, **kwargs)`
- `TemplateView`
- `RedirectView`
- `FormView`
- `ListView`
- `DetailView`
- `CreateView`
- `UpdateView`
- `DeleteView`

#### Common mixins

- `ContextMixin`
- `TemplateResponseMixin`
- `SingleObjectMixin`
- `MultipleObjectMixin`
- `FormMixin`
- `ModelFormMixin`
- `SuccessMessageMixin`
- `LoginRequiredMixin`
- `PermissionRequiredMixin`
- `UserPassesTestMixin`

#### Canonical example

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from .models import Article

class ArticleDetailView(LoginRequiredMixin, DetailView):
    model = Article
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "blog/article_detail.html"
    context_object_name = "article"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("author")
            .prefetch_related("tags")
        )
```

#### CBV lifecycle mental model

1. `as_view()` builds the callable.
2. `setup()` binds request, args, kwargs.
3. `dispatch()` selects the HTTP verb method.
4. mixins and generic base classes prepare object/queryset/form.
5. `render_to_response()` returns a response.

> 💡 Override the narrowest hook that solves the problem. Prefer `get_queryset()`, `get_context_data()`, `form_valid()`, or `get_success_url()` before replacing `dispatch()`.

### 4.3 Generic Views Reference

#### Display views

| View | Purpose | Main hooks |
|---|---|---|
| `ListView` | List objects | `get_queryset()`, `get_context_data()` |
| `DetailView` | Show single object | `get_queryset()`, `get_object()` |

```python
from django.views.generic import ListView
from .models import Article

class ArticleListView(ListView):
    model = Article
    paginate_by = 20
    context_object_name = "articles"

    def get_queryset(self):
        return (
            Article.objects
            .filter(status=Article.Status.PUBLISHED)
            .order_by("-published_at")
        )
```

#### Editing views

| View | Purpose | Main hooks |
|---|---|---|
| `FormView` | Display/process form | `get_form_class()`, `form_valid()` |
| `CreateView` | Create object | `form_valid()`, `get_success_url()` |
| `UpdateView` | Update object | `get_object()`, `form_valid()` |
| `DeleteView` | Confirm + delete | `get_object()`, `get_success_url()` |

```python
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from .models import Article

class ArticleCreateView(CreateView):
    model = Article
    fields = ["title", "slug", "body", "status"]
    success_url = reverse_lazy("article-list")

    def form_valid(self, form):
        form.instance.author = self.request.user.author
        return super().form_valid(form)
```

#### Gotchas

> ⚠️ `DeleteView` deletes on `POST`, not `GET`. A `GET` should show confirmation only.

> ⚠️ `CreateView`/`UpdateView` auto-generate `ModelForm` only when they can infer the model via `model`, `queryset`, or `get_object()`.

### Cross-references

- See [5. URL Routing](#5-url-routing)
- See [7. Forms & Validation](#7-forms--validation)
- See [8. Authentication & Authorization](#8-authentication--authorization)

---

## 5. URL Routing

URL routing maps request paths to view callables. Django URL dispatch ignores the domain and query string; routing is based on the path component only.

### Core API surface

- `path(route, view, kwargs=None, name=None)`
- `re_path(route, view, kwargs=None, name=None)`
- `include(module, namespace=None)`
- `reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None)`
- `reverse_lazy(...)`

### Canonical example

```python
# blog/urls.py
from django.urls import path
from .views import ArticleListView, article_detail

urlpatterns = [
    path("", ArticleListView.as_view(), name="article-list"),
    path("<slug:slug>/", article_detail, name="article-detail"),
]
```

```python
# mysite/urls.py
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("articles/", include("blog.urls")),
]
```

### Path converters

| Converter | Example |
|---|---|
| `str` | `<str:username>` |
| `int` | `<int:pk>` |
| `slug` | `<slug:slug>` |
| `uuid` | `<uuid:id>` |
| `path` | `<path:subpath>` |

### Canonical reverse usage

```python
from django.urls import reverse

reverse("article-detail", kwargs={"slug": "hello-django"})
# "/articles/hello-django/"
```

### Gotchas

> ⚠️ Name URL patterns. Reverse resolution is more stable than hard-coded URLs.

> ⚠️ Avoid overly clever regex routing unless `path()` cannot express the need.

> ⚠️ `APPEND_SLASH` only matters with `CommonMiddleware` and specific request patterns.

### Version-specific notes

- No major routing surface change is required for 6.0 usage.
- Per-request URLconf override remains available via `request.urlconf`.

### Cross-references

- See [4. Views](#4-views)
- See [19. Settings — Complete Reference](#19-settings--complete-reference)

---

## 6. Templates & Template Language

The Django Template Language (DTL) is intentionally restricted: it supports presentation logic, lookup, filters, tags, inheritance, inclusion, and autoescaping, but not arbitrary Python execution. Template behavior is governed by the selected backend, loaders, context processors, and template source locations.

### Core API surface

- `{% extends %}`
- `{% block %}` / `{% endblock %}`
- `{% include %}`
- `{% for %}`
- `{% if %}`
- `{% url %}`
- `{% with %}`
- `{% csrf_token %}`
- filters like `|date`, `|default`, `|safe`, `|escape`
- `render()`
- `get_template(name)`
- template backend configuration in `TEMPLATES`

### Variable resolution rules

`foo.bar` resolves in this order:

1. dict lookup
2. attribute or method lookup
3. numeric index lookup

If the resolved object is callable and safe to call without arguments, DTL may call it.

> ⚠️ This is not Python expression evaluation. Do not expect arbitrary method calls or full operator semantics.

### Template partials (Django 6.0)

Django 6.0 adds template partials for reusable fragments defined and rendered within a template file.

#### Core syntax

```django
{% partialdef article_card %}
  <article>
    <h2>{{ article.title }}</h2>
    <p>{{ article.body|truncatewords:30 }}</p>
  </article>
{% endpartialdef %}

{% partial article_card %}
```

#### Loading a partial directly

```python
from django.template.loader import get_template

partial = get_template("blog/article_detail.html#article_card")
html = partial.render({"article": article})
```

> 💡 Partials are ideal for HTMX-like fragment rendering, reusable inline UI pieces, and response variants that should not live in separate template files.

### Canonical full example

```django
{# templates/blog/article_detail.html #}
{% extends "base.html" %}

{% block content %}
  {% partialdef article_header %}
    <header>
      <h1>{{ article.title }}</h1>
      <p>By {{ article.author.name }}</p>
    </header>
  {% endpartialdef %}

  {% partial article_header %}

  <section>
    {{ article.body|linebreaks }}
  </section>
{% endblock %}
```

### Important settings

- `TEMPLATES`
- backend: `"django.template.backends.django.DjangoTemplates"`
- `DIRS`
- `APP_DIRS`
- `OPTIONS["context_processors"]`
- `OPTIONS["loaders"]`
- `OPTIONS["string_if_invalid"]`
- `FORM_RENDERER`

### Gotchas

> ⚠️ `safe` disables escaping. Only use it on trusted HTML.

> ⚠️ If `APP_DIRS=True`, templates must live under `app/templates/app/...` for predictable namespacing.

> ⚠️ When using CSP nonces, full-page caching of nonce-containing output is unsafe.

### Cross-references

- See [7. Forms & Validation](#7-forms--validation)
- See [14. Security Best Practices](#14-security-best-practices)
- See [18. Internationalization & Localization](#18-internationalization--localization)

---

## 7. Forms & Validation

Django forms provide declarative validation, HTML rendering, cleaned data, bound/unbound behavior, and powerful integration with models and formsets. The key mental model is: **incoming request data binds a form, the form validates and cleans it, then view logic decides what to persist or return**.

### Core API surface

- `forms.Form`
- `forms.ModelForm`
- `form.is_valid()`
- `form.cleaned_data`
- `form.errors`
- `form.add_error(field, error)`
- `form.has_changed()`
- `form.changed_data`
- `form.save(commit=True)` for `ModelForm`
- `formset_factory()`
- `modelformset_factory()`
- `inlineformset_factory()`

### Validation lifecycle

1. field `to_python()`
2. field `validate()`
3. field `run_validators()`
4. form `clean_<field>()`
5. form `clean()`

### Canonical form example

```python
from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)

    def clean_name(self):
        value = self.cleaned_data["name"].strip()
        if len(value.split()) < 2:
            raise forms.ValidationError("Enter full name.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        if "example.com" in cleaned_data.get("email", ""):
            self.add_error("email", "Example domains are not allowed.")
        return cleaned_data
```

```python
from django.shortcuts import redirect, render
from .forms import ContactForm

def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            # process form.cleaned_data
            return redirect("thanks")
    else:
        form = ContactForm()

    return render(request, "contact.html", {"form": form})
```

### ModelForm example

```python
from django import forms
from .models import Article

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ["title", "slug", "body", "status"]
```

### Formsets

Use formsets when one request edits multiple homogeneous forms.

```python
from django.forms import formset_factory
from .forms import ContactForm

ContactFormSet = formset_factory(ContactForm, extra=2)
```

> ⚠️ Always render `{{ formset.management_form }}` or the POST will fail validation.

### Form rendering

Django renders forms using the template engine system. Rendering can be customized at the widget, form, or renderer level.

#### Useful APIs

- `{{ form.as_p }}`
- `{{ form.as_div }}`
- `{{ form.as_table }}`
- `field.as_widget(attrs={...})`
- `field.errors`
- `form.non_field_errors()`

### Gotchas

> ⚠️ `blank=True` on a model does not automatically mean your custom `Form` field is optional; form field `required` still matters.

> ⚠️ Bound forms are immutable in intent; change input data before instantiation or work on a copy.

> ⚠️ Rendering a bound form may trigger validation if it has not already been run.

### Version-specific notes

- Composite PKs do not behave like normal scalar fields in `ModelForm` contexts.
- Django 6.0 form APIs remain compatible with the current renderer-based approach.

### Cross-references

- See [4. Views](#4-views)
- See [3. Models & ORM](#3-models--orm)
- See [15. Testing](#15-testing-unit-integration-client)

---

## 8. Authentication & Authorization

Django ships with an authentication system that handles users, groups, permissions, session-based login, password hashing, authorization decorators/mixins, and admin integration. The default model is good for many systems, but custom user models must be planned early.

### Core API surface

- `django.contrib.auth.get_user_model()`
- `authenticate(request=None, **credentials)`
- `login(request, user, backend=None)`
- `logout(request)`
- `PermissionRequiredMixin`
- `LoginRequiredMixin`
- `UserPassesTestMixin`
- `login_required(function=None, redirect_field_name="next", login_url=None)`
- `permission_required(perm, login_url=None, raise_exception=False)`
- `user.has_perm("app.codename")`
- `user.has_perms([...])`

### Canonical example

```python
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

@login_required
@permission_required("blog.change_article", raise_exception=True)
def editorial_dashboard(request):
    return render(request, "blog/dashboard.html")
```

### CBV example

```python
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView
from .models import Article

class EditorialDashboardView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "blog.view_article"
    model = Article
    template_name = "blog/dashboard.html"
```

### User model guidance

Use a custom user model at project start if email login, identity shape, or domain-specific fields differ materially from Django’s default.

```python
# settings.py
AUTH_USER_MODEL = "accounts.User"
```

> ⚠️ Changing `AUTH_USER_MODEL` mid-project is costly.

### LoginRequiredMiddleware ecosystem

When `LoginRequiredMiddleware` is installed, views require authentication by default. Public views may opt out with `login_not_required()`.

### Important settings

- `AUTH_USER_MODEL`
- `AUTH_PASSWORD_VALIDATORS`
- `LOGIN_URL`
- `LOGIN_REDIRECT_URL`
- `LOGOUT_REDIRECT_URL`
- session settings under `SESSION_*`

### Gotchas

> ⚠️ Always use `get_user_model()` or `settings.AUTH_USER_MODEL` in reusable code.

> ⚠️ Authorization is not the same as authentication; do not rely on “logged in” as “allowed”.

### Cross-references

- See [9. Admin Interface](#9-admin-interface)
- See [13. Sessions](#13-sessions)
- See [14. Security Best Practices](#14-security-best-practices)

---

## 9. Admin Interface

The Django admin is a metadata-driven internal application for CRUD, search, filtering, and operational maintenance. It is not a substitute for public product UX, but it is extremely effective for back-office workflows.

### Core API surface

- `admin.site.register(Model, ModelAdmin=None)`
- `@admin.register(Model)`
- `ModelAdmin`
- `InlineModelAdmin`, `TabularInline`, `StackedInline`
- `list_display`
- `search_fields`
- `list_filter`
- `autocomplete_fields`
- `readonly_fields`
- `raw_id_fields`
- `fieldsets`
- `prepopulated_fields`
- `actions`

### Canonical example

```python
from django.contrib import admin
from .models import Article, Tag

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "published_at")
    list_filter = ("status", "published_at")
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("tags",)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)
```

### Useful override hooks

- `get_queryset(self, request)`
- `save_model(self, request, obj, form, change)`
- `get_readonly_fields(self, request, obj=None)`
- `get_fieldsets(self, request, obj=None)`
- `has_view_permission(...)`
- `has_change_permission(...)`
- `has_delete_permission(...)`

### Admin prerequisites

- Required contrib apps in `INSTALLED_APPS`
- Session, auth, and messages middleware
- `DjangoTemplates` backend with required context processors

### Gotchas

> ⚠️ Admin actions run in privileged contexts. Validate carefully and keep them idempotent when possible.

> ⚠️ `autocomplete_fields` requires related admins to define `search_fields`.

### Version-specific notes

- Django 6.0 adds `AdminSite.password_change_form`.

### Cross-references

- See [8. Authentication & Authorization](#8-authentication--authorization)
- See [21. Contrib Packages](#21-contrib-packages)

---

## 10. Middleware

Middleware is Django’s low-level global hook system for request and response processing. The order matters: request processing goes top-down, response processing goes bottom-up.

### Core API shape

New-style middleware is a callable returning a callable:

```python
class ExampleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # before view
        response = self.get_response(request)
        # after view
        return response
```

### Built-in middleware you will often use

- `SecurityMiddleware`
- `SessionMiddleware`
- `CommonMiddleware`
- `CsrfViewMiddleware`
- `AuthenticationMiddleware`
- `MessageMiddleware`
- `ClickjackingMiddleware`
- cache middleware pair:
  - `UpdateCacheMiddleware`
  - `FetchFromCacheMiddleware`
- `ContentSecurityPolicyMiddleware` (Django 6.0)

### Canonical custom middleware

```python
class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID")
        response = self.get_response(request)
        if request.request_id:
            response["X-Request-ID"] = request.request_id
        return response
```

### Middleware ordering principles

| Must come before | Must come after | Reason |
|---|---|---|
| `SessionMiddleware` | `SecurityMiddleware` | sessions need request prepared |
| `AuthenticationMiddleware` | `SessionMiddleware` | auth depends on session |
| `MessageMiddleware` | `SessionMiddleware` | messages may use session |
| cache fetch | almost first | serve cached response early |
| cache update | almost last | store final response |

### Gotchas

> ⚠️ Middleware that is sync-only degrades async request handling, because Django must adapt execution modes.

> ⚠️ Middleware should be fast, side-effect-aware, and globally safe; heavy business logic belongs elsewhere.

### Version-specific notes

- Django 6.0 adds `ContentSecurityPolicyMiddleware`.
- Middleware can declare sync/async compatibility using documented patterns and helpers.

### Cross-references

- See [14. Security Best Practices](#14-security-best-practices)
- See [16. Async & ASGI](#16-async--asgi)
- See [12. Caching Strategies](#12-caching-strategies)

---

## 11. Static Files & Media

Static files are build/deployment assets such as CSS, JS, and images. Media files are user- or app-generated uploaded content. They should be treated differently in both configuration and deployment.

### Static files core settings

- `STATIC_URL`
- `STATIC_ROOT`
- `STATICFILES_DIRS`
- `STORAGES["staticfiles"]`

### Media core settings

- `MEDIA_URL`
- `MEDIA_ROOT`
- storage backend under `STORAGES["default"]`

### Canonical static config

```python
# settings.py
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
```

### Dev-only URL serving pattern

```python
# urls.py
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # app urls
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

> ⚠️ Do not rely on Django to serve static or media in production unless you explicitly choose and understand that design.

### Common commands

```bash
python manage.py collectstatic
```

### Gotchas

> ⚠️ Static files are collected; media files are uploaded. Never mix them into the same root or storage without a deliberate reason.

> ⚠️ `collectstatic` should be part of deployment or release build flow, not an afterthought.

### Cross-references

- See [20. Deployment](#20-deployment-wsgiasgi-checklist-production-config)
- See [21. Contrib Packages](#21-contrib-packages)

---

## 12. Caching Strategies

Django’s caching framework supports site-wide caching, per-view caching, template fragment caching, and low-level API caching. The right strategy depends on correctness boundaries, invalidation complexity, and whether the response varies by auth, headers, locale, or cookies.

### Core API surface

- setting `CACHES`
- `cache.get(key, default=None, version=None)`
- `cache.set(key, value, timeout=DEFAULT_TIMEOUT, version=None)`
- `cache.add(...)`
- `cache.delete(key, version=None)`
- `cache.get_or_set(key, default, timeout=DEFAULT_TIMEOUT, version=None)`
- decorators:
  - `cache_page(timeout, cache=None, key_prefix=None)`
  - `vary_on_headers(*headers)`
  - `vary_on_cookie`
- template tag:
  - `{% cache timeout fragment_name [vary-on] %}`

### Canonical low-level cache example

```python
from django.core.cache import cache

def get_expensive_value(article_id: int):
    key = f"article-summary:{article_id}"
    value = cache.get(key)
    if value is None:
        value = compute_summary(article_id)
        cache.set(key, value, timeout=300)
    return value
```

### Per-view caching example

```python
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

@vary_on_headers("Accept")
@cache_page(60)
def article_feed(request):
    ...
```

### Backend examples

- local memory cache
- filesystem cache
- database cache
- Memcached
- Redis via third-party backends (integration pattern, not core backend)

### Gotchas

> ⚠️ If output varies by user, session, `Accept`, language, or CSP nonce, naïve page caching is wrong.

> ⚠️ Cache invalidation must be designed with writes in mind. Prefer key design tied to explicit domain events.

### Version-specific notes

- If you use CSP nonces (`CSP.NONCE`), do not cache full HTML containing those nonces as shared content.
- Async usage may change DB connection strategy, but caching remains a separate concern.

### Cross-references

- See [14. Security Best Practices](#14-security-best-practices)
- See [16. Async & ASGI](#16-async--asgi)

---

## 13. Sessions

Sessions attach server-side or cookie-backed state to requests and users. They are commonly used for authentication, flash messaging, carts, and wizard flows.

### Core API surface

- `request.session`
- `request.session["key"] = value`
- `request.session.get("key", default)`
- `request.session.pop("key", default)`
- `request.session.flush()`
- `request.session.cycle_key()`
- `request.session.set_expiry(value)`

### Canonical example

```python
def remember_filter(request):
    request.session["article_filter"] = request.GET.get("status", "all")
    return redirect("article-list")
```

### Session backends

- DB-backed
- cache-backed
- cached DB
- file-based
- signed cookie sessions

### Important settings

- `SESSION_ENGINE`
- `SESSION_COOKIE_NAME`
- `SESSION_COOKIE_AGE`
- `SESSION_COOKIE_SECURE`
- `SESSION_COOKIE_HTTPONLY`
- `SESSION_COOKIE_SAMESITE`
- `SESSION_SAVE_EVERY_REQUEST`
- `SESSION_EXPIRE_AT_BROWSER_CLOSE`

### Gotchas

> ⚠️ Signed cookie sessions shift storage to the client; size and confidentiality assumptions change.

> ⚠️ If session state matters for security, use secure cookies and HTTPS consistently.

### Cross-references

- See [8. Authentication & Authorization](#8-authentication--authorization)
- See [14. Security Best Practices](#14-security-best-practices)

---

## 14. Security Best Practices

Django ships with strong defaults, but correct security still depends on configuration, template hygiene, query construction, deployment, and threat-model-aware design. Treat security as a system property, not a middleware checkbox.

### Built-in security domains

- XSS protection via autoescaping and safe string handling
- CSRF protection via middleware and tokens
- SQL injection resistance via ORM parameterization
- clickjacking protection via headers/middleware
- host header validation
- secure cookie settings
- HTTPS / HSTS / redirect hardening
- cryptographic signing

### 14.1 CSRF

#### Core API surface

- `django.middleware.csrf.CsrfViewMiddleware`
- `{% csrf_token %}`
- decorators:
  - `csrf_protect`
  - `csrf_exempt`
  - `ensure_csrf_cookie`
  - `requires_csrf_token`

#### Canonical example

```django
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Save</button>
</form>
```

### 14.2 XSS

Django autoescapes template variables by default. You must actively opt out with `safe`, `mark_safe()`, or custom handling.

> ⚠️ Never mark user-controlled HTML as safe without strict sanitization.

### 14.3 SQL injection

ORM-generated queries are parameterized. Risk re-enters when using raw SQL, interpolated fragments, or unsafe expression building.

> ⚠️ Avoid `extra()` in new code. Prefer expressions, annotations, and modern ORM features.

### 14.4 Clickjacking

Use `XFrameOptionsMiddleware`/`ClickjackingMiddleware` and related decorators as needed.

### 14.5 HTTPS and cookie hardening

High-value settings:

- `SECURE_SSL_REDIRECT`
- `SECURE_HSTS_SECONDS`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `SECURE_HSTS_PRELOAD`
- `SESSION_COOKIE_SECURE`
- `CSRF_COOKIE_SECURE`
- `SECURE_REFERRER_POLICY`
- `SECURE_CONTENT_TYPE_NOSNIFF`
- `X_FRAME_OPTIONS`

### 14.6 Content Security Policy (Django 6.0)

Django 6.0 includes first-party CSP support.

#### Core API surface

- `django.middleware.csp.ContentSecurityPolicyMiddleware`
- `django.utils.csp.CSP`
- `SECURE_CSP`
- `SECURE_CSP_REPORT_ONLY`
- `csp_override(config)`
- `csp_report_only_override(config)`
- `django.template.context_processors.csp`

#### Canonical settings example

```python
from django.utils.csp import CSP

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    # ...
]

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF],
    "img-src": [CSP.SELF, "https:"],
}
```

#### Template nonce example

```django
<script nonce="{{ csp_nonce }}">
  console.log("inline script allowed only for this response");
</script>
```

> ⚠️ `CSP.NONCE` requires a unique per-request value. Do not share-cache full HTML responses containing that nonce.

> ⚠️ `csp_override({})` disables policy for a view. That is usually a last resort.

### 14.7 Secret key management

- `SECRET_KEY` must be unique and secret.
- `SECRET_KEY_FALLBACKS` enables rotation.
- Remove old fallback keys after the transition window.

### Cross-references

- See [10. Middleware](#10-middleware)
- See [12. Caching Strategies](#12-caching-strategies)
- See [20. Deployment](#20-deployment-wsgiasgi-checklist-production-config)

---

## 15. Testing (Unit, Integration, Client)

Django testing combines Python’s test framework with DB isolation, settings overrides, request factories, test clients, fixtures, and specialized test cases. Test the narrowest behavior that buys confidence.

### Core API surface

- `django.test.TestCase`
- `django.test.TransactionTestCase`
- `django.test.SimpleTestCase`
- `django.test.LiveServerTestCase`
- `django.test.Client`
- `django.test.AsyncClient`
- `django.test.RequestFactory`
- `django.test.AsyncRequestFactory`
- `override_settings(...)`
- `modify_settings(...)`
- `tag(...)`

### Canonical example

```python
from django.test import TestCase
from django.urls import reverse
from .models import Article

class ArticleViewsTests(TestCase):
    def test_published_article_detail(self):
        article = Article.objects.create(
            title="Hello",
            slug="hello",
            body="World",
            status=Article.Status.PUBLISHED,
        )
        response = self.client.get(reverse("article-detail", kwargs={"slug": article.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello")
```

### Async testing example

```python
from django.test import TestCase

class AsyncPingTests(TestCase):
    async def test_ping(self):
        response = await self.async_client.get("/ping/")
        self.assertEqual(response.status_code, 200)
```

### RequestFactory example

```python
from django.test import RequestFactory, TestCase
from .views import article_detail

class ArticleViewUnitTests(TestCase):
    def test_detail_returns_404(self):
        request = RequestFactory().get("/articles/missing/")
        response = article_detail(request, slug="missing")
        # if exception-based, use assertRaises around call instead
```

### Test selection guidance

| Case | Preferred tool |
|---|---|
| Pure function or validator | unit test |
| View logic with middleware-independent flow | `RequestFactory` |
| URL + template + middleware-ish web behavior | `Client` |
| JS/browser/system interaction | external browser tool / Selenium / Playwright pattern |
| Transaction semantics | `TransactionTestCase` |

### Gotchas

> ⚠️ `TestCase` wraps tests in transactions and flushes efficiently; for true transaction behavior, use `TransactionTestCase`.

> ⚠️ Async tests require async-compatible decorators and helper functions.

### Cross-references

- See [16. Async & ASGI](#16-async--asgi)
- See [17. Management Commands](#17-management-commands)

---

## 16. Async & ASGI

Django supports async views and an async request stack under ASGI. The key rule is: **async only pays off when the whole path stays async-friendly**. If sync-only middleware or sync-only operations dominate, Django must bridge execution modes and many benefits disappear.

### Core API surface

- async views: `async def my_view(request): ...`
- async client/testing support
- async queryset methods where available
- `asgiref.sync.sync_to_async`
- `asgiref.sync.async_to_sync`

### Canonical async view

```python
from django.http import JsonResponse

async def healthcheck(request):
    return JsonResponse({"status": "ok"})
```

### Async ORM guidance

- Use async queryset methods when they trigger DB access and the async variant exists.
- Use `async for` over querysets where appropriate.
- Wrap sync-only DB transaction logic with `sync_to_async()` when necessary.

```python
from asgiref.sync import sync_to_async
from django.db import transaction

def create_article_sync(**kwargs):
    with transaction.atomic():
        return Article.objects.create(**kwargs)

async def create_article_view(request):
    article = await sync_to_async(create_article_sync)(
        title="Async",
        slug="async",
        body="Body",
    )
    ...
```

### Async safety rules

> ⚠️ Some Django subsystems are async-unsafe because they depend on thread-local or global mutable state. Violations may raise `SynchronousOnlyOperation`.

> ⚠️ `DJANGO_ALLOW_ASYNC_UNSAFE` is not a normal production solution.

### Deployment rule

- Use **ASGI** for real async gains.
- Under **WSGI**, async views run with adaptation overhead and do not support long-lived async efficiently.

### Connection guidance

- Persistent DB connections (`CONN_MAX_AGE`) should be reconsidered in async deployments.
- Use DB/backend pooling at the correct infrastructure layer.

### Cross-references

- See [10. Middleware](#10-middleware)
- See [15. Testing](#15-testing-unit-integration-client)
- See [20. Deployment](#20-deployment-wsgiasgi-checklist-production-config)

---

## 17. Management Commands

Management commands expose project operations through `manage.py`. Use them for repeatable operational, maintenance, migration, import/export, and backfill tasks.

### Built-in commands you will use frequently

- `runserver`
- `shell`
- `migrate`
- `makemigrations`
- `showmigrations`
- `sqlmigrate`
- `check`
- `createsuperuser`
- `collectstatic`
- `test`
- `diffsettings`
- `dumpdata`
- `loaddata`

### Custom command skeleton

```python
# blog/management/commands/rebuild_article_cache.py
from django.core.management.base import BaseCommand
from blog.models import Article

class Command(BaseCommand):
    help = "Rebuild cached article summaries"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        limit = options["limit"]
        for article in Article.objects.order_by("-id")[:limit]:
            self.stdout.write(f"Rebuilding {article.pk}")
        self.stdout.write(self.style.SUCCESS("Done"))
```

### Command UX guidance

- Prefer explicit arguments and dry-run modes.
- Write to `self.stdout`/`self.stderr`, not raw `print()`.
- Make destructive commands idempotent or guarded.

### Gotchas

> ⚠️ Commands run outside normal HTTP request assumptions. If your code depends on request state, refactor business logic into reusable services.

### Cross-references

- See [15. Testing](#15-testing-unit-integration-client)
- See [20. Deployment](#20-deployment-wsgiasgi-checklist-production-config)

---

## 18. Internationalization & Localization

Django provides translation, message extraction, language selection, and locale-aware formatting for dates, numbers, and templates. Separate translatable user-facing strings from internal identifiers.

### Core API surface

- `gettext`
- `gettext_lazy`
- `ngettext`
- `pgettext`
- template tags:
  - `{% trans %}`
  - `{% blocktrans %}`
- middleware:
  - `LocaleMiddleware`
- commands:
  - `makemessages`
  - `compilemessages`

### Canonical example

```python
from django.utils.translation import gettext_lazy as _
from django.db import models

class Category(models.Model):
    name = models.CharField(_("name"), max_length=100)
```

```django
{% load i18n %}
<h1>{% trans "Articles" %}</h1>
```

### Important settings

- `LANGUAGE_CODE`
- `LANGUAGES`
- `USE_I18N`
- `USE_L10N` (legacy context awareness; current formatting behavior depends on modern settings/documentation)
- `LOCALE_PATHS`
- `TIME_ZONE`
- `USE_TZ`

### Gotchas

> ⚠️ Use lazy translation (`gettext_lazy`) at import time for model field metadata, form labels, and class attributes.

> ⚠️ Do not translate database identifiers, slugs, permission codes, or protocol-level tokens unless the design explicitly requires it.

### Cross-references

- See [6. Templates & Template Language](#6-templates--template-language)
- See [19. Settings — Complete Reference](#19-settings--complete-reference)

---

## 19. Settings — Complete Reference

This is a practical clustering of the settings most relevant to implementation work. It is not a verbatim dump of every setting in Django 6.0, but it covers the high-value operational surface.

### 19.1 Core settings

| Setting | Purpose |
|---|---|
| `DEBUG` | Development diagnostics and behavior toggles |
| `SECRET_KEY` | Signing, token, cookie integrity |
| `SECRET_KEY_FALLBACKS` | Key rotation |
| `ALLOWED_HOSTS` | Host header validation |
| `ROOT_URLCONF` | Root URL module |
| `WSGI_APPLICATION` | WSGI entrypoint |
| `ASGI_APPLICATION` | ASGI entrypoint |
| `INSTALLED_APPS` | Enabled apps |
| `MIDDLEWARE` | Middleware stack |
| `DEFAULT_AUTO_FIELD` | Default PK type |

### 19.2 Database

| Setting | Purpose |
|---|---|
| `DATABASES` | DB config per alias |
| `ATOMIC_REQUESTS` | Wrap each request in transaction |
| `CONN_MAX_AGE` | Persistent connection lifetime |
| `OPTIONS` | Backend-specific DB options |
| `TEST` | Test DB behavior |

### 19.3 Templates

| Setting | Purpose |
|---|---|
| `TEMPLATES` | Template backend config |
| `DIRS` | Extra template directories |
| `APP_DIRS` | App template discovery |
| `OPTIONS["context_processors"]` | Global template context |
| `OPTIONS["loaders"]` | Loader strategy |
| `FORM_RENDERER` | Form rendering engine |

### 19.4 Static/media/storage

| Setting | Purpose |
|---|---|
| `STATIC_URL` | Static URL prefix |
| `STATIC_ROOT` | Collected static root |
| `STATICFILES_DIRS` | Extra static sources |
| `MEDIA_URL` | Media URL prefix |
| `MEDIA_ROOT` | Media storage root |
| `STORAGES` | Default/staticfiles storage backends |

### 19.5 Auth/session/messages

| Setting | Purpose |
|---|---|
| `AUTH_USER_MODEL` | Custom user model |
| `AUTH_PASSWORD_VALIDATORS` | Password policy |
| `LOGIN_URL` | Login redirect target |
| `LOGIN_REDIRECT_URL` | Post-login redirect |
| `LOGOUT_REDIRECT_URL` | Post-logout redirect |
| `SESSION_ENGINE` | Session backend |
| `SESSION_COOKIE_SECURE` | Secure session cookies |
| `MESSAGE_STORAGE` | Messages backend |
| `MESSAGE_TAGS` | Message CSS tag mapping |

### 19.6 Security

| Setting | Purpose |
|---|---|
| `CSRF_TRUSTED_ORIGINS` | Safe cross-origin POST origins |
| `CSRF_COOKIE_SECURE` | Secure CSRF cookie |
| `CSRF_USE_SESSIONS` | Store CSRF token in session |
| `SECURE_SSL_REDIRECT` | Force HTTPS |
| `SECURE_HSTS_SECONDS` | HSTS activation |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | HSTS scope |
| `SECURE_HSTS_PRELOAD` | HSTS preload |
| `SECURE_CONTENT_TYPE_NOSNIFF` | MIME sniffing defense |
| `SECURE_REFERRER_POLICY` | Referrer handling |
| `X_FRAME_OPTIONS` | Clickjacking control |
| `SECURE_CSP` | CSP policy (Django 6.0) |
| `SECURE_CSP_REPORT_ONLY` | Report-only CSP policy |

### 19.7 Internationalization

| Setting | Purpose |
|---|---|
| `LANGUAGE_CODE` | Default language |
| `LANGUAGES` | Allowed languages |
| `USE_I18N` | Translation system toggle |
| `TIME_ZONE` | Default time zone |
| `USE_TZ` | Time zone aware datetimes |
| `LOCALE_PATHS` | Extra locale directories |

### 19.8 Caching

| Setting | Purpose |
|---|---|
| `CACHES` | Cache backend map |
| `CACHE_MIDDLEWARE_ALIAS` | Cache alias for middleware |
| `CACHE_MIDDLEWARE_KEY_PREFIX` | Cache key prefix |
| `CACHE_MIDDLEWARE_SECONDS` | Page cache TTL |

### 19.9 Logging

| Setting | Purpose |
|---|---|
| `LOGGING` | Python logging config dict |
| `ADMINS` | Exception email recipients |
| `MANAGERS` | Broken link / operational mail contexts |

### 19.10 Tasks (Django 6.0)

| Setting | Purpose |
|---|---|
| `TASKS` | Task backend definitions |

### Canonical production-minded security fragment

```python
DEBUG = False
ALLOWED_HOSTS = ["example.com"]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
```

### Gotchas

> ⚠️ Some settings only have effect when paired with the right middleware or contrib app. Example: `APPEND_SLASH` needs `CommonMiddleware`.

> ⚠️ Settings often interact. Changing cookies, sessions, auth, CSP, and caching in isolation can produce surprising behavior.

### Cross-references

- See [2. Project Setup & Configuration](#2-project-setup--configuration)
- See [14. Security Best Practices](#14-security-best-practices)

---

## 20. Deployment (WSGI/ASGI, Checklist, Production config)

Production deployment is where correctness, security, and performance converge. The deployment checklist exists to force review of the settings and assumptions that are harmless in local development but dangerous or slow in real environments.

### WSGI vs ASGI

| Interface | Best for |
|---|---|
| WSGI | Traditional synchronous Django workloads |
| ASGI | Async views, websockets via adjacent stack, long-lived async-friendly workloads |

### Pre-deploy checklist

- `DEBUG = False`
- strong `SECRET_KEY`
- old keys managed via `SECRET_KEY_FALLBACKS` if rotating
- `ALLOWED_HOSTS` explicitly set
- secure cookies enabled for HTTPS
- HSTS configured when appropriate
- static assets collected
- DB credentials/environment separation complete
- logs configured and tested
- backup/recovery strategy documented
- run:
  ```bash
  python manage.py check --deploy
  ```

### Canonical ASGI entrypoint

```python
# mysite/asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
application = get_asgi_application()
```

### Canonical WSGI entrypoint

```python
# mysite/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
application = get_wsgi_application()
```

### Static/media deployment model

- static: build/release artifact, usually served by CDN/web server/object storage
- media: uploaded content, usually object storage or dedicated serving tier

### Logging guidance

Use structured, centralized logging in production and verify exception pipelines before launch.

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
```

> ⚠️ SQL logging under `django.db.backends` is only practically useful with `DEBUG=True`; do not expect it to be a normal production tracing strategy.

### Gotchas

> ⚠️ Do not deploy with `runserver`.

> ⚠️ Streaming responses and `ATOMIC_REQUESTS` interact in subtle ways because generation may continue after transaction boundaries.

> ⚠️ Async deployment does not automatically make sync code fast.

### Cross-references

- See [12. Caching Strategies](#12-caching-strategies)
- See [14. Security Best Practices](#14-security-best-practices)
- See [16. Async & ASGI](#16-async--asgi)

---

## 21. Contrib Packages

Django’s official contrib packages cover many common application capabilities. Use them before inventing infrastructure yourself, but understand their boundaries.

### 21.1 `auth`

Users, groups, permissions, authentication flows, password hashing, auth views, decorators, and admin integration.

### 21.2 `contenttypes`

Generic relation support and model-type registry. Useful for generic tagging, comments, audit trails, and polymorphic references.

### 21.3 `sessions`

Anonymous or authenticated per-client state storage.

### 21.4 `messages`

Request-scoped flash messages stored in cookies, sessions, or a hybrid fallback backend.

```python
from django.contrib import messages

def save_view(request):
    messages.success(request, "Saved successfully.")
```

### 21.5 `sites`

Represents multiple logical sites on one Django installation. Useful for multi-domain awareness and content scoping.

### 21.6 `sitemaps`

Generate XML sitemaps for search engines.

### 21.7 `staticfiles`

App-aware static file discovery and collection.

### 21.8 `humanize`

Template filters for human-friendly rendering such as naturaltime, intcomma, apnumber-like formatting patterns.

### 21.9 `syndication`

Generate RSS/Atom feeds.

### 21.10 `redirects`

Database-managed redirects.

### 21.11 `flatpages`

Simple database-driven pages, typically for lightweight content management.

### 21.12 `admindocs`

Browsable documentation for models/views/template tags in admin-adjacent workflows.

### 21.13 `postgres`

PostgreSQL-specific fields, indexes, lookups, and search features.

### 21.14 `gis` (GeoDjango)

Geospatial fields, queries, backends, and spatial functionality.

### Canonical messages example

```django
{% if messages %}
  <ul class="messages">
    {% for message in messages %}
      <li class="{{ message.tags }}">{{ message }}</li>
    {% endfor %}
  </ul>
{% endif %}
```

### Gotchas

> ⚠️ Many contrib packages require both app registration and matching middleware/context processors.

> ⚠️ `contenttypes` and generic relations are powerful but can weaken explicit relational guarantees if overused.

### Cross-references

- See [8. Authentication & Authorization](#8-authentication--authorization)
- See [9. Admin Interface](#9-admin-interface)
- See [11. Static Files & Media](#11-static-files--media)

---

## 22. Common Patterns & Anti-patterns

### Good patterns

- Use service functions for multi-step business workflows.
- Use `select_related()` / `prefetch_related()` intentionally.
- Name URL patterns and reverse them.
- Keep forms responsible for validation, not side effects.
- Keep templates presentation-only.
- Use transactions around truly atomic DB work.
- Enqueue post-commit side effects with `transaction.on_commit()`.

### Anti-patterns

> ⚠️ Fat signals for core business workflows.

> ⚠️ Raw SQL as the first choice.

> ⚠️ Putting authorization only in templates and not in views/services.

> ⚠️ Massive `views.py` files with embedded business logic, serialization, caching, and email sending mixed together.

> ⚠️ Using the admin as the public product interface.

> ⚠️ Global cache of responses that vary by user, nonce, or language.

### Canonical post-commit task pattern

```python
from functools import partial
from django.db import transaction
from django.tasks import task

@task
def send_welcome_email(user_id: int):
    ...

def register_user(...):
    with transaction.atomic():
        user = ...
        user.save()
        transaction.on_commit(partial(send_welcome_email.enqueue, user_id=user.pk))
```

### Cross-references

- See [3. Models & ORM](#3-models--orm)
- See [14. Security Best Practices](#14-security-best-practices)
- See [16. Async & ASGI](#16-async--asgi)

---

## 23. Glossary

| Term | Meaning |
|---|---|
| App | Reusable feature module inside a project |
| Project | Deployment/configuration shell containing settings and top-level URLs |
| QuerySet | Lazy, chainable database query object |
| Manager | Entry point for model table operations |
| Migration | Schema/data evolution step |
| Middleware | Global request/response hook layer |
| Context processor | Function injecting template context globally |
| Bound form | Form instantiated with input data |
| Unbound form | Form instantiated without submitted data |
| CBV | Class-based view |
| FBV | Function-based view |
| ASGI | Async Server Gateway Interface |
| WSGI | Web Server Gateway Interface |
| CSP | Content Security Policy |
| Nonce | Per-response cryptographic token for allowing inline resources |
| Contrib | Official Django built-in higher-level packages |

---

## 24. Quick Reference Cheatsheet

### Project bootstrap

```bash
python -m venv .venv
source .venv/bin/activate
pip install "Django>=6.0,<6.1"
django-admin startproject mysite .
python manage.py startapp blog
python manage.py migrate
python manage.py runserver
```

### Model

```python
class Item(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Query

```python
Item.objects.filter(name__icontains="foo").order_by("name")
```

### URL

```python
path("items/<int:pk>/", views.item_detail, name="item-detail")
```

### FBV

```python
def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    return render(request, "items/detail.html", {"item": item})
```

### CBV

```python
class ItemListView(ListView):
    model = Item
    paginate_by = 20
```

### Form

```python
class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["name"]
```

### Auth

```python
@login_required
def dashboard(request):
    ...
```

### Transaction

```python
from django.db import transaction

with transaction.atomic():
    ...
```

### Cache

```python
cache.get_or_set("key", lambda: expensive(), 300)
```

### Test

```python
response = self.client.get(reverse("item-detail", kwargs={"pk": item.pk}))
self.assertEqual(response.status_code, 200)
```

### CSP (Django 6.0)

```python
from django.utils.csp import CSP
SECURE_CSP = {"default-src": [CSP.SELF], "script-src": [CSP.SELF, CSP.NONCE]}
```

### Template partials (Django 6.0)

```django
{% partialdef row %}<tr><td>{{ value }}</td></tr>{% endpartialdef %}
{% partial row %}
```

### Tasks (Django 6.0)

```python
from django.tasks import task

@task
def recalc(pk: int):
    ...
```

---

# Appendix A — High-value APIs by subsystem

## ORM querying

- `filter()`
- `exclude()`
- `get()`
- `create()`
- `get_or_create()`
- `update_or_create()`
- `bulk_create()`
- `bulk_update()`
- `select_related()`
- `prefetch_related()`
- `annotate()`
- `aggregate()`
- `values()`
- `values_list()`
- `defer()`
- `only()`
- `order_by()`
- `distinct()`
- `exists()`
- `count()`

## HTTP shortcuts

- `render()`
- `redirect()`
- `get_object_or_404()`
- `get_list_or_404()`

## URL utilities

- `path()`
- `re_path()`
- `include()`
- `reverse()`
- `reverse_lazy()`

## Auth mixins/decorators

- `login_required`
- `permission_required`
- `LoginRequiredMixin`
- `PermissionRequiredMixin`
- `UserPassesTestMixin`

## Forms

- `Form.is_valid()`
- `Form.cleaned_data`
- `Form.errors`
- `ModelForm.save(commit=True)`
- `formset_factory()`
- `modelformset_factory()`
- `inlineformset_factory()`

## Security

- `csrf_protect`
- `csrf_exempt`
- `ensure_csrf_cookie`
- `ContentSecurityPolicyMiddleware`
- `csp_override`
- `csp_report_only_override`

## Testing

- `TestCase`
- `TransactionTestCase`
- `Client`
- `AsyncClient`
- `RequestFactory`
- `override_settings`
- `modify_settings`

---

# Appendix B — Agent instructions for code generation

Use these rules when this file is injected into an AI coding agent:

1. Generate Django 6.0-compatible code only.
2. Prefer official contrib features before third-party packages unless the user asks otherwise.
3. Default to:
   - FBV for simple irregular logic
   - CBV for CRUD/list/detail/form flows
4. For N+1 risks, proactively apply `select_related()` / `prefetch_related()`.
5. For writes spanning multiple rows/tables, consider `transaction.atomic()`.
6. For post-write side effects, prefer `transaction.on_commit()`.
7. For async code:
   - assume ASGI is required for real benefit
   - avoid mixing sync-only heavy code into async flows
8. For public HTML forms, include CSRF protection unless the user explicitly has a non-browser API case.
9. For admin changes, optimize for internal operability, not end-user UX.
10. For production settings, never emit `DEBUG=True` unless clearly marked as local development.

---

# Appendix C — Version-specific Django 6.0 highlights

## First-party Content Security Policy

- middleware: `django.middleware.csp.ContentSecurityPolicyMiddleware`
- settings: `SECURE_CSP`, `SECURE_CSP_REPORT_ONLY`
- constants: `django.utils.csp.CSP`
- decorators: `csp_override`, `csp_report_only_override`
- template nonce support via `django.template.context_processors.csp`

## Template partials

- tags: `{% partialdef %}` and `{% partial %}`
- fragment loading via `template_name#partial_name`

## Tasks framework

- decorator: `@django.tasks.task`
- setting: `TASKS`
- enqueue/results lifecycle
- worker/execution mechanism is not built into Django core

## Compatibility

- Python 3.12–3.14 supported for Django 6.0

---

# Appendix D — Practical code templates

## CRUD URL set

```python
from django.urls import path
from .views import (
    ArticleListView,
    ArticleDetailView,
    ArticleCreateView,
    ArticleUpdateView,
    ArticleDeleteView,
)

urlpatterns = [
    path("", ArticleListView.as_view(), name="article-list"),
    path("new/", ArticleCreateView.as_view(), name="article-create"),
    path("<slug:slug>/", ArticleDetailView.as_view(), name="article-detail"),
    path("<slug:slug>/edit/", ArticleUpdateView.as_view(), name="article-update"),
    path("<slug:slug>/delete/", ArticleDeleteView.as_view(), name="article-delete"),
]
```

## CRUD views

```python
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Article

class ArticleListView(ListView):
    model = Article
    paginate_by = 20

    def get_queryset(self):
        return Article.objects.order_by("-id")

class ArticleDetailView(DetailView):
    model = Article
    slug_field = "slug"
    slug_url_kwarg = "slug"

class ArticleCreateView(CreateView):
    model = Article
    fields = ["title", "slug", "body", "status"]

class ArticleUpdateView(UpdateView):
    model = Article
    fields = ["title", "slug", "body", "status"]
    slug_field = "slug"
    slug_url_kwarg = "slug"

class ArticleDeleteView(DeleteView):
    model = Article
    success_url = reverse_lazy("article-list")
    slug_field = "slug"
    slug_url_kwarg = "slug"
```

## Base template with messages

```django
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{% block title %}Site{% endblock %}</title>
  </head>
  <body>
    {% if messages %}
      <ul class="messages">
        {% for message in messages %}
          <li class="{{ message.tags }}">{{ message }}</li>
        {% endfor %}
      </ul>
    {% endif %}

    {% block content %}{% endblock %}
  </body>
</html>
```

## Pagination snippet

```django
{% if is_paginated %}
  <nav>
    {% if page_obj.has_previous %}
      <a href="?page={{ page_obj.previous_page_number }}">Previous</a>
    {% endif %}

    <span>Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}</span>

    {% if page_obj.has_next %}
      <a href="?page={{ page_obj.next_page_number }}">Next</a>
    {% endif %}
  </nav>
{% endif %}
```

---

# Appendix E — Reliability notes for agents

> ⚠️ Do not hallucinate undocumented Django 6.0 APIs.

> ⚠️ If the user asks for Channels, Celery, DRF, Redis cache backend, or HTMX, treat them as adjacent ecosystem tools, not Django core.

> ⚠️ If the user asks for every single setting or every CBV method in exhaustive form, consult the official reference pages for the exact surface.

> 💡 This file is optimized for expert assistance and operational correctness, not for reproducing the entire official documentation verbatim.

# Appendix F — Field option matrix

| Option | Field layer | Database effect | Form/admin effect | Notes |
|---|---|---|---|---|
| `null=True` | Model field | Allows `NULL` in DB | No direct form effect | Prefer for non-string nullable values |
| `blank=True` | Validation | None | Allows empty form value | Separate from `null` |
| `default=value` | Model field | Usually no DB default | Prepopulates Python-side value | Use callables for mutable/default-now patterns |
| `db_default=value` | Model field | Database default | No immediate form magic | Useful for DB-owned defaults |
| `unique=True` | Schema | Unique constraint | Validation integration | May imply index |
| `db_index=True` | Schema | Index creation | None | Use deliberately |
| `choices=` | Validation/schema-ish | Often stored as plain scalar | Renders select widget by default | Use `TextChoices` / `IntegerChoices` |
| `editable=False` | Metadata | None | Excluded from ModelForm/admin by default | Not a security boundary |
| `help_text=` | Metadata | None | Visible in forms/admin | Good for operator UX |
| `verbose_name=` | Metadata | None | Human label | Supports translation |
| `validators=` | Validation | None | Validation hooks | Keep deterministic and side-effect free |

# Appendix G — Common model Meta options

```python
class Article(models.Model):
    title = models.CharField(max_length=200)

    class Meta:
        ordering = ["-id"]
        verbose_name = "article"
        verbose_name_plural = "articles"
        indexes = [
            models.Index(fields=["title"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["title"],
                name="uniq_article_title",
            ),
        ]
```

| Meta option | Use |
|---|---|
| `ordering` | Default queryset ordering |
| `verbose_name` / `verbose_name_plural` | Human labels |
| `db_table` | Explicit DB table name |
| `indexes` | Additional indexes |
| `constraints` | Check/unique constraints |
| `unique_together` | Legacy pattern; prefer `UniqueConstraint` |
| `index_together` | Legacy pattern; prefer `Index` |
| `permissions` | Extra model permissions |
| `default_related_name` | Reverse relation naming convention |

> ⚠️ Prefer `constraints` and `indexes` over older tuple-based meta shortcuts in new code.

# Appendix H — Query expression toolbox

Useful expression classes and helpers for advanced ORM work:

- `F`
- `Q`
- `Value`
- `Case`
- `When`
- `Subquery`
- `OuterRef`
- `Exists`
- `Func`
- `ExpressionWrapper`
- `Window`
- aggregates: `Count`, `Sum`, `Avg`, `Min`, `Max`

```python
from django.db.models import F, Q, Count

qs = (
    Article.objects
    .filter(Q(status=Article.Status.PUBLISHED) | Q(status=Article.Status.DRAFT))
    .annotate(comment_count=Count("comments"))
    .filter(comment_count__gt=0)
    .order_by(F("published_at").desc(nulls_last=True))
)
```

> 💡 Use expressions before resorting to raw SQL. They compose better, remain database-aware, and preserve ORM semantics.

# Appendix I — Transactions quick reference

## Patterns

### Atomic write block

```python
from django.db import transaction

with transaction.atomic():
    # multiple writes
    ...
```

### Savepoint-aware nested atomic block

```python
with transaction.atomic():
    ...
    with transaction.atomic():
        ...
```

### Post-commit callback

```python
from django.db import transaction

def do_after_commit():
    ...

transaction.on_commit(do_after_commit)
```

## When to use `ATOMIC_REQUESTS`

Use it when:
- most views perform a coherent write transaction
- you want request-level atomicity
- transaction overhead is acceptable

Avoid or reconsider when:
- many views are read-only
- streaming responses are common
- long-running views would hold transactions too long

# Appendix J — Request/response quick reference

## `HttpRequest`

Useful attributes and methods:

- `request.method`
- `request.GET`
- `request.POST`
- `request.FILES`
- `request.headers`
- `request.COOKIES`
- `request.session`
- `request.user`
- `request.path`
- `request.path_info`
- `request.scheme`
- `request.body`
- `request.get_full_path()`
- `request.build_absolute_uri(location=None)`
- `request.get_host()`
- `request.get_signed_cookie(key, default=RAISE_ERROR, salt="", max_age=None)`
- `request.accepts(mime_type)`
- `request.get_preferred_type(media_types)`

## `HttpResponse`

Useful variants:

- `HttpResponse`
- `JsonResponse`
- `StreamingHttpResponse`
- `FileResponse`
- `HttpResponseRedirect`
- `HttpResponsePermanentRedirect`
- status-specialized shortcuts in `django.http` and exceptions such as `Http404`

```python
from django.http import FileResponse

def download(request):
    return FileResponse(open("/tmp/report.pdf", "rb"), as_attachment=True, filename="report.pdf")
```

> ⚠️ `StreamingHttpResponse` changes how middleware, transactions, and buffering semantics behave.

# Appendix K — Common exceptions

- `Http404`
- `PermissionDenied`
- `SuspiciousOperation`
- `BadRequest`
- `ValidationError`
- `ObjectDoesNotExist`
- `MultipleObjectsReturned`
- `ImproperlyConfigured`
- `SynchronousOnlyOperation`

# Appendix L — Built-in generic view families

## Base views

- `View`
- `TemplateView`
- `RedirectView`

## Generic display views

- `ListView`
- `DetailView`

## Generic editing views

- `FormView`
- `CreateView`
- `UpdateView`
- `DeleteView`

## Date-based generic views

- archive/list/date views in the date generic view family

> 💡 Date-based generic views remain useful for classic archive/content sites, though many teams now prefer explicit queries with `ListView`.

# Appendix M — Common auth views and URLs

Django provides built-in auth views for login/logout/password workflows.

Typical URL wiring:

```python
from django.urls import path
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
]
```

> ⚠️ These views depend on templates with the expected names unless you override `template_name`.

# Appendix N — Signals quick reference

## Model signals

- `pre_init`
- `post_init`
- `pre_save`
- `post_save`
- `pre_delete`
- `post_delete`
- `m2m_changed`

## Migration/app signals

- `pre_migrate`
- `post_migrate`

## Request signals

- `request_started`
- `request_finished`
- `got_request_exception`

## Safer signal usage rules

1. Keep handlers small and deterministic.
2. Avoid critical hidden business workflows.
3. Guard against duplicate registration.
4. Prefer `transaction.on_commit()` for side effects that depend on committed writes.

# Appendix O — Caching design checklist

Before adding caching, answer:

1. What exact object/response is cached?
2. What invalidates it?
3. Does it vary by user, language, `Accept`, cookies, permissions, or nonce?
4. What is the stale-read tolerance?
5. Can recomputation happen concurrently and safely?
6. Is low-level cache preferable to per-view cache?

# Appendix P — Forms quick comparison

| Type | Best for |
|---|---|
| `Form` | Non-model input or custom workflows |
| `ModelForm` | Standard create/update flows tightly tied to a model |
| `formset_factory` | Multiple homogeneous simple forms |
| `modelformset_factory` | Bulk editing/query-backed groups of model forms |
| `inlineformset_factory` | Parent-child editing over FK relations |

# Appendix Q — Uploaded files quick reference

## Request layer

Uploaded files arrive in `request.FILES`.

```python
def upload_view(request):
    if request.method == "POST":
        uploaded = request.FILES["file"]
        ...
```

## Model layer

```python
class Document(models.Model):
    file = models.FileField(upload_to="documents/")
```

## Gotchas

> ⚠️ User uploads are an attack surface. Validate type, size, storage location, and serving policy.

> ⚠️ Do not trust file extensions alone.

# Appendix R — Admin productivity patterns

Useful `ModelAdmin` options:

- `date_hierarchy`
- `list_select_related`
- `ordering`
- `list_per_page`
- `save_as`
- `save_on_top`
- `filter_horizontal`
- `filter_vertical`

```python
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    date_hierarchy = "published_at"
    list_select_related = ("author",)
    ordering = ("-published_at",)
    list_per_page = 50
```

# Appendix S — Logging quick reference

High-signal logger names:

- `django`
- `django.request`
- `django.server`
- `django.template`
- `django.db.backends`
- `django.security.*`

Minimal production-ish structure:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
```

# Appendix T — Tasks framework quick reference (Django 6.0)

## Core concepts

- task definition
- backend configuration
- enqueue
- result lookup
- async enqueue variant
- JSON-serializable arguments/results
- external worker responsibility

## Development pattern

```python
TASKS = {
    "default": {
        "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
    }
}
```

> ⚠️ `ImmediateBackend` is suitable for development and gradual adoption, not as a substitute for real background execution infrastructure.

# Appendix U — Middleware order template

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",  # Django 6.0
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

> 💡 Exact ordering may change with cache middleware, locale middleware, or custom middleware, but dependency-aware ordering still applies.

# Appendix V — URL naming conventions

Use stable names:

- `<resource>-list`
- `<resource>-detail`
- `<resource>-create`
- `<resource>-update`
- `<resource>-delete`

Examples:

- `article-list`
- `article-detail`
- `article-create`

This makes reverse resolution consistent across templates, views, redirects, tests, and permissions-sensitive flows.

# Appendix W — Template architecture patterns

## Recommended structure

```text
templates/
  base.html
  includes/
    messages.html
  blog/
    article_list.html
    article_detail.html
    article_form.html
```

## Rules

1. Use app-namespaced template names.
2. Keep layout composition explicit with inheritance and includes/partials.
3. Avoid business logic and query orchestration in templates.
4. Keep reusable fragments in partials or includes.

# Appendix X — Data access performance checklist

Before shipping a queryset-heavy view, verify:

- Is pagination required?
- Are related objects prefetched?
- Are only required fields loaded?
- Does ordering align with indexes?
- Are annotations unavoidable and measured?
- Is duplicate evaluation happening?

# Appendix Y — Safe defaults for new Django 6.0 projects

- `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"`
- `USE_TZ = True`
- `DEBUG = False` outside local development
- secure cookies over HTTPS
- named URL patterns
- app template namespacing
- explicit `AUTH_USER_MODEL` decision at project start
- explicit storage strategy for media/static
- explicit logging and deployment checklist

# Appendix Z — Final operational reminders

1. Prefer explicitness over magic.
2. Keep domain logic outside views when it grows.
3. Keep migrations readable and reversible where practical.
4. Cache only what you can invalidate.
5. Use async intentionally, not cosmetically.
6. Treat admin as an operator surface.
7. Treat settings as a system, not isolated flags.
8. For Django 6.0-specific work, remember the three big additions:
   - first-party CSP
   - template partials
   - tasks framework
