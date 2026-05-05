import os
import sys
from pathlib import Path
import environ
from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

env = environ.Env(
    DEBUG=(bool, False)
)

DEFAULT_ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "testserver"]

BASE_DIR = Path(__file__).resolve().parent.parent

RUNNING_TESTS = "test" in sys.argv
READ_DOT_ENV_FILE = env.bool("READ_DOT_ENV_FILE", default=not RUNNING_TESTS)

# Ignore the local .env by default while running tests so the suite stays stable
# across workspaces with different development overrides.
if READ_DOT_ENV_FILE:
    environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

DEPLOYMENT_PROFILE = env("DEPLOYMENT_PROFILE", default="pilot").lower()
if DEPLOYMENT_PROFILE not in {"pilot", "production"}:
    raise ImproperlyConfigured("DEPLOYMENT_PROFILE must be 'pilot' or 'production'.")

if RUNNING_TESTS:
    DEBUG = env.bool("TEST_DEBUG", default=True)
else:
    DEBUG = env.bool("DEBUG", default=DEPLOYMENT_PROFILE == "pilot")
if DEBUG:
    SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key')
else:
    SECRET_KEY = env('SECRET_KEY', default=None)
    if not SECRET_KEY:
        raise ImproperlyConfigured("SECRET_KEY is required when DEBUG=False.")

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=DEFAULT_ALLOWED_HOSTS)
if DEBUG:
    for host in DEFAULT_ALLOWED_HOSTS:
        if host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.identity',
    'apps.corporate',
    'apps.marketplace',
    'apps.evaluation',
    'apps.notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.csp.ContentSecurityPolicyMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
ASGI_APPLICATION = 'config.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.notifications.context_processors.notifications_summary',
                'config.context_processors.public_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

default_database_url = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
if DEPLOYMENT_PROFILE == "production" and not env("DATABASE_URL", default=None):
    raise ImproperlyConfigured("DATABASE_URL is required when DEPLOYMENT_PROFILE=production.")
DATABASES = {
    'default': env.db('DATABASE_URL', default=default_database_url)
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

production_security_defaults = DEPLOYMENT_PROFILE == "production" and not DEBUG
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=production_security_defaults)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=production_security_defaults)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=production_security_defaults)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000 if production_security_defaults else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    'SECURE_HSTS_INCLUDE_SUBDOMAINS',
    default=production_security_defaults,
)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=production_security_defaults)
SECURE_REFERRER_POLICY = env(
    'SECURE_REFERRER_POLICY',
    default='same-origin' if DEBUG else 'strict-origin-when-cross-origin',
)
SECURE_CONTENT_TYPE_NOSNIFF = env.bool('SECURE_CONTENT_TYPE_NOSNIFF', default=production_security_defaults)
X_FRAME_OPTIONS = env('X_FRAME_OPTIONS', default='DENY')
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.UNSAFE_INLINE, "https://challenges.cloudflare.com"],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "img-src": [CSP.SELF, "data:"],
    "font-src": [CSP.SELF, "data:"],
    "frame-src": [CSP.SELF, "https://challenges.cloudflare.com"],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
}

# Custom user model
AUTH_USER_MODEL = 'identity.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'marketplace:challenge-list'
LOGOUT_REDIRECT_URL = 'login'

SUPPORT_EMAIL = env("SUPPORT_EMAIL", default="soporte@vimer.local")
LEGAL_TERMS_VERSION = env("LEGAL_TERMS_VERSION", default="v1")
LEGAL_PRIVACY_VERSION = env("LEGAL_PRIVACY_VERSION", default="v1")
TURNSTILE_SITE_KEY = env("TURNSTILE_SITE_KEY", default="")
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")
TURNSTILE_VERIFY_URL = env(
    "TURNSTILE_VERIFY_URL",
    default="https://challenges.cloudflare.com/turnstile/v0/siteverify",
)
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER or SUPPORT_EMAIL)
MARKETPLACE_ATTACHMENT_MAX_COUNT = env.int("MARKETPLACE_ATTACHMENT_MAX_COUNT", default=5)
MARKETPLACE_ATTACHMENT_MAX_BYTES = env.int("MARKETPLACE_ATTACHMENT_MAX_BYTES", default=10 * 1024 * 1024)
