#!/usr/bin/env bash
# Clyra-Vendor — shared helpers for the extraction pipeline.
# Sourced by the other scripts; not meant to be executed directly.

set -o errexit
set -o nounset
set -o pipefail

# Resolve the repository root from this file's location.
CLYRA_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLYRA_ROOT="$(cd "${CLYRA_SCRIPT_DIR}/.." && pwd)"

clyra_log()  { printf '\033[1;36m[clyra]\033[0m %s\n' "$*" >&2; }
clyra_warn() { printf '\033[1;33m[clyra]\033[0m %s\n' "$*" >&2; }
clyra_err()  { printf '\033[1;31m[clyra]\033[0m %s\n' "$*" >&2; }
clyra_die()  { clyra_err "$*"; exit 1; }

# ---------------------------------------------------------------------------
# JSON reading without external dependencies.
#
#   clyra_json <file> <dotted.key>        -> scalar
#   clyra_json_array <file> <dotted.key>  -> one array element per line
#
# Arrays are joined with '\n' then split again by the caller. This keeps the
# toolchain to a stock python3 install.
# ---------------------------------------------------------------------------
clyra_json() {
    python3 - "$@" <<'PY'
import json, sys
path, key = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as fh:
    node = json.load(fh)
for part in key.split("."):
    if isinstance(node, list):
        node = node[int(part)]
    else:
        node = node[part]
if isinstance(node, bool):
    print("true" if node else "false")
elif isinstance(node, (list, dict)):
    print("\n".join(str(x) for x in node) if isinstance(node, list) else json.dumps(node))
else:
    print("" if node is None else node)
PY
}

clyra_json_array() {
    clyra_json "$@" | sed '/^$/d'
}

# ---------------------------------------------------------------------------
# Integrity helpers
# ---------------------------------------------------------------------------

# clyra_sha256 <file> -> hex digest
clyra_sha256() {
    python3 - "$1" <<'PY'
import hashlib, sys
h = hashlib.sha256()
with open(sys.argv[1], "rb") as fh:
    for chunk in iter(lambda: fh.read(8 << 20), b""):
        h.update(chunk)
print(h.hexdigest())
PY
}

# clyra_verify_sha256 <file> <expected|"-"> <label>
clyra_verify_sha256() {
    local file="$1" expected="$2" label="${3:-file}"
    [[ -f "$file" ]] || clyra_die "${label}: missing ${file}"
    if [[ -z "$expected" || "$expected" == "-" ]]; then
        clyra_warn "${label}: no sha256 recorded; computing $(clyra_sha256 "$file")"
        return 0
    fi
    local actual
    actual="$(clyra_sha256 "$file")"
    if [[ "${actual,,}" != "${expected,,}" ]]; then
        clyra_die "${label}: sha256 mismatch
  expected: ${expected}
  actual:   ${actual}
Refusing to continue with an unverified archive."
    fi
    clyra_log "${label}: sha256 OK (${actual:0:16}…)"
}

# ---------------------------------------------------------------------------
# Browser User-Agent
#
# Xiaomi's OSS buckets (and a few mirrors) reject or throttle bare curl/wget
# requests. A normal browser UA keeps downloads reliable and resumable.
# ---------------------------------------------------------------------------
CLYRA_UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# clyra_download <url> <dest>
# Resumable, retried, and tolerant of flaky CDN edges.
clyra_download() {
    local url="$1" dest="$2"
    mkdir -p "$(dirname "$dest")"

    if [[ -s "$dest" ]]; then
        clyra_log "resuming partial download: ${dest}"
    fi

    local attempt
    for attempt in 1 2 3 4 5 6; do
        if curl \
            --fail --location --continue-at - \
            --retry 5 --retry-delay 5 --retry-all-errors \
            --connect-timeout 30 --speed-time 120 --speed-limit 4096 \
            --user-agent "${CLYRA_UA}" \
            --output "$dest" "$url"
        then
            [[ -s "$dest" ]] || clyra_die "download produced an empty file: ${dest}"
            clyra_log "downloaded $(du -h "$dest" | cut -f1) -> ${dest}"
            return 0
        fi
        clyra_warn "download attempt ${attempt}/6 failed; retrying in $((attempt * 5))s"
        sleep $((attempt * 5))
    done

    clyra_die "unable to download ${url}

If every mirror fails, download it once yourself and place the archive at:
  ${dest}
then re-run with --skip-download."
}

# ---------------------------------------------------------------------------
# Workspace layout
# ---------------------------------------------------------------------------
clyra_workspace() { printf '%s\n' "${CLYRA_WORK:-${CLYRA_ROOT}/build/workspace}"; }
clyra_download_dir() { printf '%s\n' "${CLYRA_DL:-${CLYRA_ROOT}/build/downloads}"; }
