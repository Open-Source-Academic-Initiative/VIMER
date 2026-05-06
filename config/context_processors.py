from django.conf import settings


def public_settings(request):
    return {
        "support_email": settings.SUPPORT_EMAIL,
        "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
    }
