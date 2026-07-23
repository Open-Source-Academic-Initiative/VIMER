import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    request = Request(
        "http://127.0.0.1:8000/health/ready/",
        headers={
            "Host": os.environ.get("HEALTHCHECK_HOST", "localhost"),
            "X-Forwarded-Proto": (
                "https"
                if os.environ.get("DEPLOYMENT_PROFILE") == "production"
                else "http"
            ),
        },
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return 0 if response.status == 200 and payload.get("status") == "ok" else 1
    except (HTTPError, URLError, TimeoutError, ValueError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
