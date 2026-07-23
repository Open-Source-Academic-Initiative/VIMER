import logging

from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


logger = logging.getLogger(__name__)


@never_cache
@require_GET
def liveness(request):
    return JsonResponse({"status": "ok"})


@never_cache
@require_GET
def readiness(request):
    connection = connections["default"]
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        pending_migrations = executor.migration_plan(targets)
        if pending_migrations:
            return JsonResponse(
                {
                    "status": "unavailable",
                    "database": "ok",
                    "migrations": "pending",
                },
                status=503,
            )
    except Exception:
        logger.warning("Readiness check failed.", exc_info=True)
        return JsonResponse(
            {
                "status": "unavailable",
                "database": "unavailable",
            },
            status=503,
        )

    return JsonResponse(
        {
            "status": "ok",
            "database": "ok",
            "migrations": "ok",
        }
    )
