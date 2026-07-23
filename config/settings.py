import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import environ
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email
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

# Secure by default: DEBUG must be an explicit opt-in (local .env / runserver),
# never a profile side effect. A pilot container without configuration fails
# fast asking for SECRET_KEY instead of booting with DEBUG=True.
if RUNNING_TESTS:
    DEBUG = env.bool("TEST_DEBUG", default=True)
else:
    DEBUG = env.bool("DEBUG", default=False)
if DEPLOYMENT_PROFILE == "production" and DEBUG:
    raise ImproperlyConfigured(
        "DEBUG must be False when DEPLOYMENT_PROFILE=production."
    )
if DEBUG:
    SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key')
else:
    SECRET_KEY = env('SECRET_KEY', default=None)
    if not SECRET_KEY:
        raise ImproperlyConfigured("SECRET_KEY is required when DEBUG=False.")
if DEPLOYMENT_PROFILE == "production" and (
    len(SECRET_KEY) < 50
    or SECRET_KEY.startswith("django-insecure")
    or "CHANGE_ME" in SECRET_KEY.upper()
):
    raise ImproperlyConfigured(
        "Production SECRET_KEY must contain at least 50 characters and must not "
        "use Django's insecure development prefix."
    )

ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS',
    default=[] if DEPLOYMENT_PROFILE == "production" else DEFAULT_ALLOWED_HOSTS,
)
if DEPLOYMENT_PROFILE == "production" and (
    not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS
):
    raise ImproperlyConfigured(
        "Production ALLOWED_HOSTS must be explicit and cannot contain '*'."
    )
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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.csp.ContentSecurityPolicyMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'config.security.RateLimitMiddleware',
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
configured_database_url = env("DATABASE_URL", default=None)
if DEPLOYMENT_PROFILE == "production" and not configured_database_url:
    raise ImproperlyConfigured("DATABASE_URL is required when DEPLOYMENT_PROFILE=production.")
DATABASES = {
    'default': env.db('DATABASE_URL', default=default_database_url)
}
if DEPLOYMENT_PROFILE == "production":
    if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
        raise ImproperlyConfigured(
            "Production DATABASE_URL must use PostgreSQL."
        )
    DATABASES["default"]["CONN_MAX_AGE"] = env.int(
        "DATABASE_CONN_MAX_AGE",
        default=60,
    )
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

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

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'assets']
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # WhiteNoise lets gunicorn serve /static/ (Django admin assets) in the
        # pilot profile, where there is no reverse proxy in front.
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
# In development/tests there is no collected STATIC_ROOT; serve straight from
# the app finders instead of warning about the missing directory.
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_AUTOREFRESH = DEBUG

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
TEST_RUNNER = "config.testing.IsolatedMediaDiscoverRunner"

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
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if DEPLOYMENT_PROFILE == "production"
    else None
)
USE_X_FORWARDED_HOST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = DEPLOYMENT_PROFILE == "production"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool(
    "SESSION_EXPIRE_AT_BROWSER_CLOSE",
    default=DEPLOYMENT_PROFILE == "production",
)
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, "https://challenges.cloudflare.com"],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "img-src": [CSP.SELF, "data:"],
    "font-src": [CSP.SELF, "data:"],
    "connect-src": [CSP.SELF, "https://challenges.cloudflare.com"],
    "frame-src": [CSP.SELF, "https://challenges.cloudflare.com"],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
}

# Custom user model
AUTH_USER_MODEL = 'identity.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'marketplace:challenge-list'
LOGOUT_REDIRECT_URL = 'login'

# Absolute base URL used to build links inside outbound emails (verification,
# notifications), where no request object is available. Native, no external deps.
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", default="http://localhost:8000").rstrip("/")

SUPPORT_EMAIL = env("SUPPORT_EMAIL", default="soporte@vimer.local")
LEGAL_CONTROLLER_NAME = env("LEGAL_CONTROLLER_NAME", default="")
LEGAL_CONTROLLER_ID = env("LEGAL_CONTROLLER_ID", default="")
LEGAL_CONTROLLER_ADDRESS = env("LEGAL_CONTROLLER_ADDRESS", default="")
LEGAL_CONTROLLER_CONTACT_CHANNEL = env(
    "LEGAL_CONTROLLER_CONTACT_CHANNEL",
    default="",
)
PRIVACY_EMAIL = env("PRIVACY_EMAIL", default="")
LEGAL_TERMS_VERSION = env("LEGAL_TERMS_VERSION", default="v1")
LEGAL_PRIVACY_VERSION = env("LEGAL_PRIVACY_VERSION", default="v1")
TURNSTILE_SITE_KEY = env("TURNSTILE_SITE_KEY", default="")
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")
TURNSTILE_VERIFY_URL = env(
    "TURNSTILE_VERIFY_URL",
    default="https://challenges.cloudflare.com/turnstile/v0/siteverify",
)
TURNSTILE_REQUIRED = env.bool(
    "TURNSTILE_REQUIRED",
    default=not DEBUG and not RUNNING_TESTS,
)
EMAIL_DELIVERY_REQUIRED = env.bool(
    "EMAIL_DELIVERY_REQUIRED",
    default=not DEBUG and not RUNNING_TESTS,
)
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="" if EMAIL_DELIVERY_REQUIRED else EMAIL_HOST_USER or SUPPORT_EMAIL,
)
MARKETPLACE_ATTACHMENT_MAX_COUNT = env.int("MARKETPLACE_ATTACHMENT_MAX_COUNT", default=5)
MARKETPLACE_ATTACHMENT_MAX_BYTES = env.int("MARKETPLACE_ATTACHMENT_MAX_BYTES", default=10 * 1024 * 1024)
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int(
    "DATA_UPLOAD_MAX_MEMORY_SIZE",
    default=55 * 1024 * 1024,
)
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int(
    "FILE_UPLOAD_MAX_MEMORY_SIZE",
    default=2 * 1024 * 1024,
)
DATA_UPLOAD_MAX_NUMBER_FIELDS = env.int("DATA_UPLOAD_MAX_NUMBER_FIELDS", default=200)
DATA_UPLOAD_MAX_NUMBER_FILES = env.int("DATA_UPLOAD_MAX_NUMBER_FILES", default=10)
# When nginx fronts the app (production profile), attachment downloads are
# delegated to it via X-Accel-Redirect after the view authorizes the request;
# the /media/marketplace/attachments/ location is marked `internal` in nginx,
# so private files are never reachable by direct URL.
ATTACHMENT_X_ACCEL_REDIRECT = env.bool(
    "ATTACHMENT_X_ACCEL_REDIRECT",
    default=DEPLOYMENT_PROFILE == "production",
)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": env("CACHE_LOCATION", default="/tmp/vimer-cache"),
        "TIMEOUT": 300,
        "OPTIONS": {
            "MAX_ENTRIES": 10_000,
        },
    }
}
RATE_LIMIT_ENABLED = env.bool(
    "RATE_LIMIT_ENABLED",
    default=not RUNNING_TESTS,
)
TRUST_PROXY_CLIENT_IP = DEPLOYMENT_PROFILE == "production"
RATE_LIMIT_RULES = {
    "/login/": (
        env.int("RATE_LIMIT_LOGIN_ATTEMPTS", default=10),
        env.int("RATE_LIMIT_LOGIN_WINDOW_SECONDS", default=300),
    ),
    "/signup/": (
        env.int("RATE_LIMIT_SIGNUP_ATTEMPTS", default=5),
        env.int("RATE_LIMIT_SIGNUP_WINDOW_SECONDS", default=900),
    ),
    "/password-reset/": (
        env.int("RATE_LIMIT_PASSWORD_RESET_ATTEMPTS", default=5),
        env.int("RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS", default=900),
    ),
    "/verificar-correo/*": (
        env.int("RATE_LIMIT_EMAIL_VERIFICATION_ATTEMPTS", default=20),
        env.int("RATE_LIMIT_EMAIL_VERIFICATION_WINDOW_SECONDS", default=300),
    ),
}

LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


def is_missing_or_placeholder(value):
    normalized_value = value.strip().upper()
    return not normalized_value or "CHANGE_ME" in normalized_value


def is_invalid_email(value):
    try:
        validate_email(value)
    except ValidationError:
        return True
    return False


if bool(TURNSTILE_SITE_KEY) != bool(TURNSTILE_SECRET_KEY):
    raise ImproperlyConfigured(
        "TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY must be configured together."
    )
if TURNSTILE_REQUIRED and not (TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY):
    raise ImproperlyConfigured(
        "Turnstile keys are required when TURNSTILE_REQUIRED=True."
    )
turnstile_verify_url = urlparse(TURNSTILE_VERIFY_URL)
if TURNSTILE_SECRET_KEY and (
    turnstile_verify_url.scheme != "https" or not turnstile_verify_url.netloc
):
    raise ImproperlyConfigured("TURNSTILE_VERIFY_URL must use HTTPS.")

if EMAIL_DELIVERY_REQUIRED:
    if EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
        raise ImproperlyConfigured(
            "The console email backend cannot be used when email delivery is "
            "required."
        )
    if EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and any(
        is_missing_or_placeholder(email_value)
        for email_value in (EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    ):
        raise ImproperlyConfigured(
            "SMTP delivery requires non-placeholder EMAIL_HOST, "
            "EMAIL_HOST_USER, and EMAIL_HOST_PASSWORD."
        )
    if (
        is_missing_or_placeholder(DEFAULT_FROM_EMAIL)
        or is_invalid_email(DEFAULT_FROM_EMAIL)
    ):
        raise ImproperlyConfigured(
            "Email delivery requires a valid, non-placeholder DEFAULT_FROM_EMAIL."
        )
elif not DEBUG and not RUNNING_TESTS and (
    EMAIL_BACKEND != "django.core.mail.backends.console.EmailBackend"
):
    raise ImproperlyConfigured(
        "EMAIL_DELIVERY_REQUIRED=False is only valid with the console backend "
        "for an explicitly isolated maintenance environment."
    )

if DEPLOYMENT_PROFILE == "production":
    missing_legal_settings = [
        setting_name
        for setting_name, setting_value in (
            ("LEGAL_CONTROLLER_NAME", LEGAL_CONTROLLER_NAME),
            ("LEGAL_CONTROLLER_ID", LEGAL_CONTROLLER_ID),
            ("LEGAL_CONTROLLER_ADDRESS", LEGAL_CONTROLLER_ADDRESS),
            (
                "LEGAL_CONTROLLER_CONTACT_CHANNEL",
                LEGAL_CONTROLLER_CONTACT_CHANNEL,
            ),
            ("PRIVACY_EMAIL", PRIVACY_EMAIL),
        )
        if is_missing_or_placeholder(setting_value)
    ]
    if missing_legal_settings:
        raise ImproperlyConfigured(
            "Production legal controller settings are required: "
            + ", ".join(missing_legal_settings)
            + "."
        )
    if is_invalid_email(PRIVACY_EMAIL):
        raise ImproperlyConfigured(
            "Production PRIVACY_EMAIL must be a valid email address."
        )
    if not CSRF_TRUSTED_ORIGINS or any(
        urlparse(origin).scheme != "https" or not urlparse(origin).netloc
        for origin in CSRF_TRUSTED_ORIGINS
    ):
        raise ImproperlyConfigured(
            "Production CSRF_TRUSTED_ORIGINS must contain explicit HTTPS origins."
        )
    public_base_url = urlparse(PUBLIC_BASE_URL)
    if public_base_url.scheme != "https" or not public_base_url.netloc:
        raise ImproperlyConfigured("Production PUBLIC_BASE_URL must use HTTPS.")
    if "CHANGE_ME" in configured_database_url.upper():
        raise ImproperlyConfigured(
            "Production DATABASE_URL still contains a CHANGE_ME placeholder."
        )
    if not TURNSTILE_REQUIRED:
        raise ImproperlyConfigured(
            "TURNSTILE_REQUIRED cannot be disabled in production."
        )
    if any(
        is_missing_or_placeholder(turnstile_value)
        for turnstile_value in (TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY)
    ):
        raise ImproperlyConfigured(
            "Production Turnstile keys cannot be empty or placeholders."
        )
    if not all(
        (
            SECURE_SSL_REDIRECT,
            SESSION_COOKIE_SECURE,
            CSRF_COOKIE_SECURE,
            SECURE_CONTENT_TYPE_NOSNIFF,
            SECURE_HSTS_SECONDS > 0,
            ATTACHMENT_X_ACCEL_REDIRECT,
        )
    ):
        raise ImproperlyConfigured(
            "Production security settings cannot disable HTTPS redirect, secure "
            "cookies, HSTS, MIME sniffing protection, or private attachment "
            "delegation."
        )
    if not EMAIL_DELIVERY_REQUIRED:
        raise ImproperlyConfigured(
            "EMAIL_DELIVERY_REQUIRED cannot be disabled in production."
        )
