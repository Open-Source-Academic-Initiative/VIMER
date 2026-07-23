import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """Small cache-backed safety net for sensitive unauthenticated POST routes.

    Nginx applies an additional shared limit in production. This middleware also
    protects the direct-gunicorn pilot profile. It deliberately fails open if
    the cache is unavailable so an operational cache incident cannot lock every
    user out of the platform.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.RATE_LIMIT_ENABLED
            and request.method == "POST"
            and (rule := self._matching_rule(request.path)) is not None
        ):
            limit, window_seconds = settings.RATE_LIMIT_RULES[rule]
            if limit > 0 and window_seconds > 0:
                try:
                    count = self._increment(rule, self._client_ip(request), window_seconds)
                except Exception:
                    logger.warning("Rate-limit cache unavailable.", exc_info=True)
                else:
                    if count > limit:
                        response = JsonResponse(
                            {
                                "detail": (
                                    "Demasiados intentos. Inténtalo nuevamente más tarde."
                                )
                            },
                            status=429,
                        )
                        response["Retry-After"] = str(window_seconds)
                        return response

        return self.get_response(request)

    @staticmethod
    def _matching_rule(path: str) -> str | None:
        for rule in settings.RATE_LIMIT_RULES:
            if rule.endswith("*") and path.startswith(rule[:-1]):
                return rule
            if path == rule:
                return rule
        return None

    @staticmethod
    def _client_ip(request) -> str:
        if settings.TRUST_PROXY_CLIENT_IP:
            return request.META.get("HTTP_X_REAL_IP") or request.META.get(
                "REMOTE_ADDR",
                "unknown",
            )
        return request.META.get("REMOTE_ADDR", "unknown")

    @staticmethod
    def _increment(rule: str, client_ip: str, window_seconds: int) -> int:
        digest = hashlib.sha256(f"{rule}:{client_ip}".encode()).hexdigest()
        cache_key = f"vimer-rate-limit:{digest}"
        if cache.add(cache_key, 1, timeout=window_seconds):
            return 1
        try:
            return cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, timeout=window_seconds)
            return 1
