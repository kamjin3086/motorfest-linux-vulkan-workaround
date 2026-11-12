#!/usr/bin/env bash
# Set a process-local Mesa RADV manifest filter; never modify system/game files.
set -euo pipefail
if (( $# == 0 )); then
    printf 'Usage: bash %s COMMAND [ARGUMENT ...]\n' "$0" >&2
    printf 'Requires Mesa RADV manifests named radeon_icd*.\n' >&2
    exit 2
fi
exec env VK_LOADER_DRIVERS_SELECT='radeon_icd*' "$@"
