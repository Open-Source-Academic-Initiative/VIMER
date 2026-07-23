import os
import sys
import time
from pathlib import Path


def main() -> int:
    heartbeat_path = Path(
        os.environ.get(
            "SCHEDULER_HEARTBEAT_PATH",
            "/tmp/vimer-scheduler-heartbeat",
        )
    )
    try:
        join_request_interval = int(
            os.environ.get("JOIN_REQUEST_EXPIRY_INTERVAL_SECONDS", "300")
        )
        challenge_closure_interval = int(
            os.environ.get("CHALLENGE_CLOSURE_INTERVAL_SECONDS", "900")
        )
        grace_seconds = int(
            os.environ.get("SCHEDULER_HEALTH_GRACE_SECONDS", "60")
        )
        heartbeat_values = dict(
            line.split("=", maxsplit=1)
            for line in heartbeat_path.read_text(encoding="utf-8").splitlines()
        )
        last_join_request_success = int(heartbeat_values["join_requests"])
        last_challenge_closure_success = int(heartbeat_values["challenges"])
    except (OSError, ValueError):
        return 1
    except (KeyError, TypeError):
        return 1

    current_time = time.time()
    join_request_age = current_time - last_join_request_success
    challenge_closure_age = current_time - last_challenge_closure_success
    join_request_maximum_age = max(join_request_interval + grace_seconds, 120)
    challenge_closure_maximum_age = max(
        challenge_closure_interval + grace_seconds,
        120,
    )
    return (
        0
        if (
            0 <= join_request_age <= join_request_maximum_age
            and 0 <= challenge_closure_age <= challenge_closure_maximum_age
        )
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
