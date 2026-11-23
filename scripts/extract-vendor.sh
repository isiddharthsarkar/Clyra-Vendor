#!/usr/bin/env bash
# Clyra-Vendor — download a full HyperOS ROM and extract only the vendor blobs.
#
#   ./scripts/extract-vendor.sh                 # full run (download + extract)
#   ./scripts/extract-vendor.sh --from-archive  # archive already downloaded
#   ./scripts/extract-vendor.sh --super path/to/super.img
#
# Every stage is resumable: re-running picks up where the previous run stopped.
#
# Environment overrides
#   CLYRA_DL     download directory        (default build/downloads)
#   CLYRA_WORK   scratch/work directory    (default build/workspace)
#   CLYRA_OUT    vendor output directory   (default vendor)
#   CLYRA_KEEP_SCRATCH=1  keep expanded super.img instead of deleting it

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

usage() {
    sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

FROM_ARCHIVE=0
SUPER_OVERRIDE=""
LAYOUT="logical"

while (($#)); do
    case "$1" in
        --from-archive) FROM_ARCHIVE=1 ;;
        --super) SUPER_OVERRIDE="${2:?--super needs a path}"; shift ;;
        --layout) LAYOUT="${2:?--layout needs logical|filesystem}"; shift ;;
        --skip-download) FROM_ARCHIVE=1 ;;
        -h|--help) usage 0 ;;
        *) clyra_die "unknown argument: $1 (try --help)" ;;
    esac
    shift
done

DEVICE_JSON="${CLYRA_ROOT}/firmware/device.json"
VENDOR_LIST="${CLYRA_ROOT}/firmware/$(basename "$(clyra_json "$DEVICE_JSON" vendor_list)")"

[[ -f "$DEVICE_JSON" ]] || clyra_die "missing $DEVICE_JSON"
[[ -f "$VENDOR_LIST" ]] || clyra_die "missing $VENDOR_LIST"

DEVICE_NAME="$(clyra_json "$DEVICE_JSON" device_name)"
CODENAME="$(clyra_json "$DEVICE_JSON" codename)"
ROM_NAME="$(clyra_json "$DEVICE_JSON" rom_full_name)"
ROM_URL="$(clyra_json "$DEVICE_JSON" rom_url)"
ROM_SHA256="$(clyra_json "$DEVICE_JSON" rom_sha256 2>/dev/null || echo '-')"

DL_DIR="$(clyra_download_dir)"
WORK_DIR="$(clyra_workspace)"
OUT_DIR="${CLYRA_OUT:-${CLYRA_ROOT}/vendor}"
ARCHIVE="${DL_DIR}/${ROM_NAME}.tgz"
EXTRACT_DIR="${WORK_DIR}/rom"
SUPER_IMG="${WORK_DIR}/super.img"

clyra_log "device   : ${DEVICE_NAME} (${CODENAME})"
clyra_log "firmware : $(clyra_json "$DEVICE_JSON" hyperos_version)"
clyra_log "archive  : ${ARCHIVE}"

# --------------------------------------------------------------------------
# 1. Download
# --------------------------------------------------------------------------
if (( ! FROM_ARCHIVE )) && [[ ! -s "$ARCHIVE" ]]; then
    mkdir -p "$DL_DIR"
    MIRRORS=("$ROM_URL")
    while IFS= read -r m; do [[ -n "$m" ]] && MIRRORS+=("$m"); done \
        < <(clyra_json_array "$DEVICE_JSON" rom_url_mirrors || true)

    for url in "${MIRRORS[@]}"; do
        clyra_log "trying ${url%%\?*}"
        # In a subshell so a failure does not abort the script.
        if (clyra_download "$url" "$ARCHIVE"); then
            break
        fi
        clyra_warn "mirror failed, falling through"
    done
    [[ -s "$ARCHIVE" ]] || clyra_die "all mirrors failed for ${ROM_NAME}"
elif [[ -s "$ARCHIVE" ]]; then
    clyra_log "using already-downloaded archive"
fi

if [[ -f "$ARCHIVE" ]]; then
    clyra_verify_sha256 "$ARCHIVE" "$ROM_SHA256" "rom archive"
fi

# --------------------------------------------------------------------------
# 2. Unpack the fastboot archive
# --------------------------------------------------------------------------
super_from_archive() {
    # `tar -tzf` on a multi-GiB tgz is slow; cache the listing.
    local listing="${WORK_DIR}/archive-listing.txt"
    mkdir -p "$WORK_DIR"
    if [[ ! -s "$listing" || "$ARCHIVE" -nt "$listing" ]]; then
        clyra_log "indexing archive (this takes a minute)…"
        tar -tzf "$ARCHIVE" > "$listing"
    fi
    # Prefer the first super image that exists on disk.
    grep -E '(^|/)super\.img$|images/super\.img$' "$listing" | head -1 || true
}

if [[ -n "$SUPER_OVERRIDE" ]]; then
    SUPER_IMG="$SUPER_OVERRIDE"
    clyra_log "using supplied super image: ${SUPER_IMG}"
elif [[ -f "$SUPER_IMG" ]]; then
    clyra_log "reusing extracted super image"
else
    [[ -s "$ARCHIVE" ]] || clyra_die "no archive at ${ARCHIVE}; run without --from-archive first"
    entry="$(super_from_archive)"
    [[ -n "$entry" ]] || clyra_die "archive does not contain a super.img:
  ${ARCHIVE}"

    mkdir -p "$EXTRACT_DIR"
    clyra_log "extracting ${entry} from archive (needs ~$(du -g "$ARCHIVE" 2>/dev/null | cut -f1) GiB free)…"

    # Stream only the members we need.
    NEED_BOOT=0
    tar -xzf "$ARCHIVE" -C "$EXTRACT_DIR" --occurrence=1 -O "$entry" > "${SUPER_IMG}.partial"
    mv -f "${SUPER_IMG}.partial" "$SUPER_IMG"

    # Some builds ship the images inside a nested images/ dir with a .tar.gz.
    for meta in boot.img vendor_boot.img; do
        if tar -tzf "$ARCHIVE" | grep -qx "images/${meta}"; then
            NEED_BOOT=1
        fi
    done
    if (( NEED_BOOT )); then
        clyra_log "pulling boot images…"
        tar -xzf "$ARCHIVE" -C "$WORK_DIR" --occurrence=1 images/boot.img images/vendor_boot.img 2>/dev/null || true
    fi
fi

[[ -s "$SUPER_IMG" ]] || clyra_die "super image is missing or empty: ${SUPER_IMG}"
clyra_log "super image: ${SUPER_IMG} ($(du -h "$SUPER_IMG" | cut -f1))"

# --------------------------------------------------------------------------
# 3. Build the partition selection
# --------------------------------------------------------------------------
mapfile -t REQUESTED < <(sed -e 's/#.*//' -e 's/[[:space:]]//g' "$VENDOR_LIST" | sed '/^$/d')
(( ${#REQUESTED[@]} )) || clyra_die "vendor list ${VENDOR_LIST} is empty"
clyra_log "requested partitions: ${REQUESTED[*]}"

PARTITION_CSV="$(IFS=,; echo "${REQUESTED[*]}")"

# --------------------------------------------------------------------------
# 4. Extract
# --------------------------------------------------------------------------
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

python3 "${CLYRA_SCRIPT_DIR}/extract_super.py" \
    --super "$SUPER_IMG" \
    --out-dir "$OUT_DIR" \
    --partitions "$PARTITION_CSV" \
    --layout "$LAYOUT" \
    --slots "${CLYRA_SLOTS:-a}" \
    --manifest "${WORK_DIR}/extract-manifest.json" \
    --scratch "$WORK_DIR/scratch"

# --------------------------------------------------------------------------
# 5. Turn the result into something a device tree can consume
# --------------------------------------------------------------------------
if [[ -f "${CLYRA_SCRIPT_DIR}/make_vendor_tree.py" ]]; then
    python3 "${CLYRA_SCRIPT_DIR}/make_vendor_tree.py" \
        --manifest "${WORK_DIR}/extract-manifest.json" \
        --root "$OUT_DIR" \
        --device "$DEVICE_JSON" \
        --blob-source "$ROM_URL" \
        || clyra_warn "make_vendor_tree.py reported an issue"
fi

# Record which images exist so the repo .gitignore stays accurate.
GENERATED_IGNORE="${CLYRA_ROOT}/vendor/.gitignore"
: > "$GENERATED_IGNORE"
printf '# Generated by scripts/extract-vendor.sh — do not edit by hand.\n' >> "$GENERATED_IGNORE"
printf '# Only partitions actually present on %s are listed.\n\n' "$(clyra_json "$DEVICE_JSON" hyperos_version)" >> "$GENERATED_IGNORE"
for img in "$OUT_DIR"/*.img; do
    [[ -e "$img" ]] || continue
    printf '/%s\n' "$(basename "$img")" >> "$GENERATED_IGNORE"
done
for dir in "$OUT_DIR"/*/; do
    [[ -d "$dir" ]] || continue
    name="$(basename "$dir")"
    [[ "$name" == "proprietary" || "$name" == ".*" ]] && continue
    printf '/%s/\n' "$name" >> "$GENERATED_IGNORE"
done

clyra_log "done. vendor staging tree: ${OUT_DIR}"
clyra_log "next: ./scripts/publish-vendor.sh --dry-run   (preview the layout)"
