#!/usr/bin/env bash
# Clyra-Vendor — publish the extracted vendor blobs to a GitHub repository.
#
# Splits the tree into commits below GitHub's per-object limits
# (100 MiB hard block, 50 MiB warning) and pushes to a dedicated branch.
#
#   ./scripts/publish-vendor.sh --dry-run
#   ./scripts/publish-vendor.sh --repo isiddharthsarkar/Clyra-Vendor
#   ./scripts/publish-vendor.sh --repo owner/repo --branch ruan-in-16.0
#
# Environment
#   CLYRA_OUT          staged vendor directory   (default: vendor/)
#   CLYRA_MAX_BLOB     per-file size limit in MiB (default: 45)
#   CLYRA_CHUNK_FILES  files per commit          (default: 400)
#   CLYRA_CHUNK_BYTES  bytes per commit in MiB   (default: 1700)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

usage() { sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

DRY_RUN=0
REPO=""
BRANCH=""
MESSAGE_SUFFIX=""

while (($#)); do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --repo) REPO="${2:?--repo needs owner/name}"; shift ;;
        --branch) BRANCH="${2:?--branch needs a name}"; shift ;;
        --message) MESSAGE_SUFFIX="${2:-}"; shift ;;
        -h|--help) usage 0 ;;
        *) clyra_die "unknown argument: $1 (try --help)" ;;
    esac
    shift
done

DEVICE_JSON="${CLYRA_ROOT}/firmware/device.json"
CODENAME="$(clyra_json "$DEVICE_JSON" codename)"
VENDOR_BRANCH="$(clyra_json "$DEVICE_JSON" vendor_branch)"
FIRMWARE="$(clyra_json "$DEVICE_JSON" hyperos_version)"
DEVICE_NAME="$(clyra_json "$DEVICE_JSON" device_name)"
OUT_DIR="${CLYRA_OUT:-${CLYRA_ROOT}/vendor}"

[[ -d "$OUT_DIR" ]] || clyra_die "no staged vendor tree at ${OUT_DIR}
Run ./scripts/extract-vendor.sh first."

BRANCH="${BRANCH:-$VENDOR_BRANCH}"
REPO="${REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || echo "isiddharthsarkar/Clyra-Vendor")}"

MAX_BLOB="${CLYRA_MAX_BLOB:-45}"
CHUNK_FILES="${CLYRA_CHUNK_FILES:-400}"
CHUNK_BYTES="${CLYRA_CHUNK_BYTES:-1700}"

# --------------------------------------------------------------------------
# Inventory + size guard
# --------------------------------------------------------------------------
mapfile -t FILES < <(cd "$OUT_DIR" && find . \( -type f -o -type l \) ! -path './.git/*' | sed 's|^\./||' | sort)
(( ${#FILES[@]} )) || clyra_die "staged tree ${OUT_DIR} contains no files"

TOTAL_BYTES=0
OVERSIZE=()
SYMLINKS=0
for f in "${FILES[@]}"; do
    if [[ -L "$OUT_DIR/$f" ]]; then
        SYMLINKS=$((SYMLINKS + 1))
        continue
    fi
    sz=$(stat -c%s "$OUT_DIR/$f")
    TOTAL_BYTES=$((TOTAL_BYTES + sz))
    if (( sz > MAX_BLOB * 1024 * 1024 )); then
        OVERSIZE+=("$f ($((sz / 1024 / 1024)) MiB)")
    fi
done

human_bytes() { numfmt --to=iec --suffix=B "$1" 2>/dev/null || echo "$1 B"; }

clyra_log "repo      : ${REPO}"
clyra_log "branch    : ${BRANCH}"
clyra_log "firmware  : ${DEVICE_NAME} ${FIRMWARE} (${CODENAME})"
clyra_log "files     : ${#FILES[@]} (${SYMLINKS} symlink(s))"
clyra_log "size      : $(human_bytes "$TOTAL_BYTES")"

if (( ${#OVERSIZE[@]} )); then
    clyra_err "these files exceed GitHub's ${MAX_BLOB} MiB per-object limit:"
    printf '    %s\n' "${OVERSIZE[@]}" >&2
    clyra_die "Split them (e.g. --layout filesystem) or raise CLYRA_MAX_BLOB only if
you know the target repo uses Git LFS."
fi

if [[ -d "$OUT_DIR/.git" ]]; then
    clyra_die "${OUT_DIR} is a git repository itself; publish from a plain directory"
fi

if (( DRY_RUN )); then
    clyra_log "dry run: no commits or pushes performed"
    clyra_log "planned commits: $(( (${#FILES[@]} / CHUNK_FILES) + 1 )) (± file budget)"
    printf '\nfirst 25 files:\n'
    printf '    %s\n' "${FILES[@]:0:25}"
    (( ${#FILES[@]} > 25 )) && printf '    … and %d more\n' "$(( ${#FILES[@]} - 25 ))"
    exit 0
fi

# --------------------------------------------------------------------------
# Isolated worktree on the vendor branch
# --------------------------------------------------------------------------
WORKTREE="${CLYRA_ROOT}/build/publish"
rm -rf "$WORKTREE"
mkdir -p "$(dirname "$WORKTREE")"

# Start from an orphan branch so the vendor blobs never mix with source code.
git -C "$CLYRA_ROOT" fetch --quiet origin "$BRANCH" 2>/dev/null || true

if git -C "$CLYRA_ROOT" rev-parse --verify --quiet "origin/${BRANCH}" >/dev/null; then
    clyra_log "continuing from existing origin/${BRANCH}"
    git clone --quiet --branch "$BRANCH" --single-branch \
        "$(git -C "$CLYRA_ROOT" remote get-url origin)" "$WORKTREE"
else
    clyra_log "creating orphan branch ${BRANCH}"
    git clone --quiet --no-checkout "$(git -C "$CLYRA_ROOT" remote get-url origin)" "$WORKTREE"
    git -C "$WORKTREE" checkout --quiet --orphan "$BRANCH"
    git -C "$WORKTREE" rm -rf --quiet . 2>/dev/null || true
    find "$WORKTREE" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
fi

git -C "$WORKTREE" config user.name  "$(git -C "$CLYRA_ROOT" config user.name)"
git -C "$WORKTREE" config user.email "$(git -C "$CLYRA_ROOT" config user.email)"

# --------------------------------------------------------------------------
# Commit in budgeted chunks
# --------------------------------------------------------------------------
commit_chunk() {
    local -n _batch=$1
    (( ${#_batch[@]} )) || return 0
    git -C "$WORKTREE" add --force -- "${_batch[@]}"
    local msg
    msg="vendor(${CODENAME}): ${FIRMWARE} — ${#_batch[@]} file(s)

Device: ${DEVICE_NAME} (${CODENAME})
Firmware: ${FIRMWARE} / Android $(clyra_json "$DEVICE_JSON" android_version)
Region: $(clyra_json "$DEVICE_JSON" market)
Archive: $(clyra_json "$DEVICE_JSON" rom_full_name).tgz
${MESSAGE_SUFFIX}"
    git -C "$WORKTREE" commit --quiet --message "$msg"
    clyra_log "committed ${#_batch[@]} file(s)"
    _batch=()
}

BATCH=()
BATCH_BYTES=0
N=0
for f in "${FILES[@]}"; do
    src="$OUT_DIR/$f"
    dest="${WORKTREE}/${f}"
    mkdir -p "$(dirname "$dest")"

    if [[ -L "$src" ]]; then
        # Vendor trees are full of symlinks; `cp -P` keeps them as links
        # instead of flattening them into duplicated real files.
        cp -P --no-dereference --force "$src" "$dest"
        sz=0
    else
        # `cp --reflink=auto` keeps this cheap on filesystems that support it.
        cp --reflink=auto --preserve=mode,timestamps --force "$src" "$dest"
        sz=$(stat -c%s "$dest")
    fi

    BATCH+=("$f")
    BATCH_BYTES=$((BATCH_BYTES + sz))
    N=$((N + 1))

    if (( ${#BATCH[@]} >= CHUNK_FILES || BATCH_BYTES >= CHUNK_BYTES * 1024 * 1024 )); then
        commit_chunk BATCH
        BATCH_BYTES=0
        # Push periodically so a failure mid-way keeps completed work.
        git -C "$WORKTREE" push --quiet origin "$BRANCH" && clyra_log "pushed ${N}/${#FILES[@]}"
    fi
done
commit_chunk BATCH

clyra_log "pushing final state to ${REPO} ${BRANCH}…"
git -C "$WORKTREE" push --quiet origin "$BRANCH"

clyra_log "done → https://github.com/${REPO}/tree/${BRANCH}"
