from django.conf import settings


def public_settings(request):
    return {
        "support_email": settings.SUPPORT_EMAIL,
        "legal_controller_name": settings.LEGAL_CONTROLLER_NAME,
        "legal_controller_id": settings.LEGAL_CONTROLLER_ID,
        "legal_controller_address": settings.LEGAL_CONTROLLER_ADDRESS,
        "legal_controller_contact_channel": (
            settings.LEGAL_CONTROLLER_CONTACT_CHANNEL
        ),
        "legal_privacy_version": settings.LEGAL_PRIVACY_VERSION,
        "legal_terms_version": settings.LEGAL_TERMS_VERSION,
        "privacy_email": settings.PRIVACY_EMAIL,
        "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
    }
