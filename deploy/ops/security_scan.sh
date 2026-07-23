#!/bin/sh
set -eu

artifact_directory="${1:-artifacts/security}"
if [ -z "$artifact_directory" ] || [ "$artifact_directory" = "/" ]; then
    echo "A specific artifact directory is required." >&2
    exit 2
fi

pip_audit_command="${PIP_AUDIT_COMMAND:-pip-audit}"
cyclonedx_command="${CYCLONEDX_COMMAND:-cyclonedx-py}"
trivy_command="${TRIVY_COMMAND:-trivy}"

for command_name in "$pip_audit_command" "$cyclonedx_command"; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required security tool is not installed: $command_name" >&2
        exit 2
    fi
done

mkdir -p "$artifact_directory"

set -- \
    --strict \
    --no-deps \
    --requirement requirements.lock \
    --format json \
    --output "$artifact_directory/python-audit.json"

# This advisory affects bleach.linkify(parse_email=True). VIMER only invokes
# bleach.clean with an explicit allowlist, so the vulnerable path is absent.
# Set the variable to an empty value to audit without this reviewed exception.
ignored_vulnerabilities="${PIP_AUDIT_IGNORED_VULNERABILITIES-GHSA-g75f-g53v-794x}"
for vulnerability_id in $ignored_vulnerabilities; do
    set -- "$@" --ignore-vuln "$vulnerability_id"
done

"$pip_audit_command" "$@"

"$cyclonedx_command" requirements requirements.lock \
    --output-reproducible \
    --output-format JSON \
    --output-file "$artifact_directory/python-sbom.cdx.json"

if [ "${SCAN_CONTAINER_IMAGE:-True}" = "True" ]; then
    if ! command -v "$trivy_command" >/dev/null 2>&1; then
        echo "Container scanning requested but Trivy is not installed." >&2
        exit 2
    fi
    image_name="${VIMER_IMAGE:-vimer:production}"
    "$trivy_command" image \
        --format cyclonedx \
        --output "$artifact_directory/container-sbom.cdx.json" \
        "$image_name"
    "$trivy_command" image \
        --scanners vuln \
        --severity HIGH,CRITICAL \
        --format json \
        --output "$artifact_directory/container-audit.json" \
        "$image_name"
    "$trivy_command" image \
        --scanners vuln \
        --ignore-unfixed \
        --exit-code 1 \
        --severity HIGH,CRITICAL \
        --format json \
        --output "$artifact_directory/container-actionable-audit.json" \
        "$image_name"
fi

(
    cd "$artifact_directory"
    sha256sum ./*.json > MANIFEST.sha256
)

echo "Security artifacts created at $artifact_directory"
