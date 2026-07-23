import os
import sys
import time


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402
from django.db import connections  # noqa: E402
from django.db.utils import OperationalError  # noqa: E402


def main() -> int:
    django.setup()
    attempts = int(os.environ.get("DATABASE_WAIT_ATTEMPTS", "30"))
    delay_seconds = float(os.environ.get("DATABASE_WAIT_DELAY_SECONDS", "2"))

    for attempt in range(1, attempts + 1):
        try:
            connection = connections["default"]
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except OperationalError:
            if attempt == attempts:
                print(
                    f"Database unavailable after {attempts} attempts.",
                    file=sys.stderr,
                )
                return 1
            print(
                f"Database unavailable (attempt {attempt}/{attempts}); retrying.",
                file=sys.stderr,
            )
            time.sleep(delay_seconds)
        else:
            print("Database connection ready.")
            return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
