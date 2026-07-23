#!/bin/sh
set -eu

validate_interval() {
    interval_name="$1"
    interval_value="$2"
    minimum_value="$3"
    case "$interval_value" in
        ""|*[!0-9]*)
            echo "$interval_name must be an integer." >&2
            exit 2
            ;;
    esac
    if [ "$interval_value" -lt "$minimum_value" ]; then
        echo "$interval_name must be at least $minimum_value." >&2
        exit 2
    fi
}

join_request_interval="${JOIN_REQUEST_EXPIRY_INTERVAL_SECONDS:-300}"
challenge_closure_interval="${CHALLENGE_CLOSURE_INTERVAL_SECONDS:-900}"
retry_delay="${SCHEDULER_RETRY_DELAY_SECONDS:-60}"
validate_interval JOIN_REQUEST_EXPIRY_INTERVAL_SECONDS "$join_request_interval" 60
validate_interval CHALLENGE_CLOSURE_INTERVAL_SECONDS "$challenge_closure_interval" 60
validate_interval SCHEDULER_RETRY_DELAY_SECONDS "$retry_delay" 10

heartbeat_path="${SCHEDULER_HEARTBEAT_PATH:-/tmp/vimer-scheduler-heartbeat}"

python manage.py migrate --check

active_child_pid=""
shutdown_requested=0

request_shutdown() {
    shutdown_requested=1
    if [ -n "$active_child_pid" ]; then
        kill -TERM "$active_child_pid" 2>/dev/null || true
    fi
}

run_management_command() {
    python manage.py "$1" &
    active_child_pid=$!
    if wait "$active_child_pid"; then
        command_status=0
    else
        command_status=$?
    fi
    active_child_pid=""
    if [ "$shutdown_requested" -eq 1 ]; then
        exit 0
    fi
    return "$command_status"
}

interruptible_sleep() {
    sleep "$1" &
    active_child_pid=$!
    if wait "$active_child_pid"; then
        sleep_status=0
    else
        sleep_status=$?
    fi
    active_child_pid=""
    if [ "$shutdown_requested" -eq 1 ]; then
        exit 0
    fi
    return "$sleep_status"
}

trap request_shutdown TERM INT

last_join_request_success=0
last_challenge_closure_success=0
next_join_request_run=0
next_challenge_closure_run=0

while true; do
    current_time="$(date +%s)"

    if [ "$current_time" -ge "$next_join_request_run" ]; then
        echo "Running scheduled job: expire_join_requests"
        if run_management_command expire_join_requests; then
            success_time="$(date +%s)"
            last_join_request_success="$success_time"
            next_join_request_run=$((success_time + join_request_interval))
        else
            echo "Scheduled job failed: expire_join_requests" >&2
            failure_time="$(date +%s)"
            next_join_request_run=$((failure_time + retry_delay))
        fi
    fi

    if [ "$current_time" -ge "$next_challenge_closure_run" ]; then
        echo "Running scheduled job: close_expired_challenges"
        if run_management_command close_expired_challenges; then
            success_time="$(date +%s)"
            last_challenge_closure_success="$success_time"
            next_challenge_closure_run=$((success_time + challenge_closure_interval))
        else
            echo "Scheduled job failed: close_expired_challenges" >&2
            failure_time="$(date +%s)"
            next_challenge_closure_run=$((failure_time + retry_delay))
        fi
    fi

    if [ "$last_join_request_success" -gt 0 ] \
        && [ "$last_challenge_closure_success" -gt 0 ]; then
        {
            echo "join_requests=$last_join_request_success"
            echo "challenges=$last_challenge_closure_success"
        } > "${heartbeat_path}.$$"
        mv "${heartbeat_path}.$$" "$heartbeat_path"
    fi

    if [ "$next_join_request_run" -le "$next_challenge_closure_run" ]; then
        next_run="$next_join_request_run"
    else
        next_run="$next_challenge_closure_run"
    fi
    current_time="$(date +%s)"
    sleep_seconds=$((next_run - current_time))
    if [ "$sleep_seconds" -lt 1 ]; then
        sleep_seconds=1
    fi
    interruptible_sleep "$sleep_seconds" || true
done
