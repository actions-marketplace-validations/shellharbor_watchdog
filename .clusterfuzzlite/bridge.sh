#!/usr/bin/env bash
set -euo pipefail
resource_directory="$1"
operation="$2"
value="$3"
# The immutable bundle location is supplied by the harness, not fuzzed input.
# shellcheck disable=SC1090,SC1091
source "${resource_directory}/lib/watchdog/00-bootstrap.sh"
# shellcheck disable=SC1090,SC1091
source "${resource_directory}/lib/watchdog/20-notifications.sh"
# shellcheck disable=SC1090,SC1091
source "${resource_directory}/lib/watchdog/50-lifecycle.sh"
case "$operation" in
    json) escape_json "$value" ;;
    html) escape_status_html "$value" ;;
    prometheus) escape_prometheus_label_value "$value" ;;
    *) exit 2 ;;
esac
