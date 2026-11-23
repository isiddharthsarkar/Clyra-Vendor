#!/usr/bin/env bash
# Clyra-Vendor — self-test against generated super.img fixtures.
# No device, no network, no root required.
#
#   ./scripts/tests/run-tests.sh

set -o errexit
set -o nounset
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

ok()   { printf '  \033[1;32mPASS\033[0m %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf '  \033[1;31mFAIL\033[0m %s\n' "$*"; FAIL=$((FAIL + 1)); }
head_() { printf '\n\033[1;36m%s\033[0m\n' "$*"; }

maxtx() { python3 "$ROOT/scripts/tests/make_fixture.py" "$@"; }

# --------------------------------------------------------------------------
head_ "1. fixture generation"
# --------------------------------------------------------------------------
maxtx --out "$TMP/raw/super.img" >/dev/null && ok "raw super.img" || bad "raw super.img"
maxtx --out "$TMP/sparse/super.img" --sparse >/dev/null && ok "sparse super.img" || bad "sparse"
maxtx --out "$TMP/slot/super.img" --slot-suffix >/dev/null && ok "slot-suffixed" || bad "slot"

# --------------------------------------------------------------------------
head_ "2. independent oracle (upstream lpunpack)"
# --------------------------------------------------------------------------
if python3 "$ROOT/tools/vendor/lpunpack.py" "$TMP/raw/super.img" "$TMP/oracle" >/dev/null 2>&1; then
    ok "upstream lpunpack read the fixture"
else
    bad "upstream lpunpack failed"
fi

# --------------------------------------------------------------------------
head_ "3. extractor matches the oracle byte-for-byte"
# --------------------------------------------------------------------------
python3 "$ROOT/scripts/extract_super.py" \
    --super "$TMP/raw/super.img" --out-dir "$TMP/mine" \
    --partitions vendor,odm,my_product >/dev/null 2>&1 || bad "extractor run"

for p in vendor odm my_product; do
    if cmp -s "$TMP/mine/$p.img" "$TMP/oracle/$p.img"; then
        ok "$p.img byte-identical to oracle"
    else
        bad "$p.img differs from oracle"
    fi
done

# --------------------------------------------------------------------------
head_ "4. payload lands in the right partition"
# --------------------------------------------------------------------------
for p in vendor odm my_product; do
    if head -c 200 "$TMP/mine/$p.img" | grep -qa "CLYRA-FIXTURE:$p"; then
        ok "$p.img carries its own payload"
    else
        bad "$p.img payload wrong"
    fi
done

# --------------------------------------------------------------------------
head_ "5. sparse image produces identical output"
# --------------------------------------------------------------------------
python3 "$ROOT/scripts/extract_super.py" \
    --super "$TMP/sparse/super.img" --out-dir "$TMP/sparse_out" \
    --partitions vendor,odm >/dev/null 2>&1 || bad "sparse extractor run"

for p in vendor odm; do
    if cmp -s "$TMP/sparse_out/$p.img" "$TMP/oracle/$p.img"; then
        ok "sparse $p.img identical to raw"
    else
        bad "sparse $p.img differs"
    fi
done

if compgen -G "$TMP/sparse_out/.scratch/*.img" >/dev/null; then
    bad "expanded intermediate left behind"
else
    ok "scratch cleaned up"
fi

# --------------------------------------------------------------------------
head_ "6. slot-suffixed metadata"
# --------------------------------------------------------------------------
python3 "$ROOT/scripts/extract_super.py" \
    --super "$TMP/slot/super.img" --out-dir "$TMP/slot_out" \
    --partitions vendor,odm --slots a >/dev/null 2>&1 || bad "slot extractor run"

[[ -f "$TMP/slot_out/vendor_a.img" ]] && ok "vendor_a.img produced" || bad "vendor_a.img missing"
[[ -f "$TMP/slot_out/vendor_b.img" ]] && bad "slot b extracted despite --slots a" \
    || ok "only requested slot extracted"

# --------------------------------------------------------------------------
head_ "7. missing partitions reported, not fatal"
# --------------------------------------------------------------------------
out="$(python3 "$ROOT/scripts/extract_super.py" \
    --super "$TMP/raw/super.img" --out-dir "$TMP/miss" \
    --partitions vendor,no_such_part 2>&1)"
if grep -q "no_such_part" <<<"$out" && [[ -f "$TMP/miss/vendor.img" ]]; then
    ok "warns about missing partition, still extracts the rest"
else
    bad "missing-partition handling"
fi

# --------------------------------------------------------------------------
head_ "8. manifest is valid JSON with expectations"
# --------------------------------------------------------------------------
python3 "$ROOT/scripts/extract_super.py" \
    --super "$TMP/raw/super.img" --out-dir "$TMP/man" \
    --partitions vendor --manifest "$TMP/man/manifest.json" >/dev/null 2>&1

python3 - "$TMP/man/manifest.json" <<'PY' && ok "manifest structure valid" || bad "manifest invalid"
import json, sys
d = json.load(open(sys.argv[1]))
assert d["layout"] == "logical"
assert d["logical_block_size"] == 4096
assert d["metadata_slot_count"] == 2
assert len(d["extracted"]) == 1
assert d["extracted"][0]["partition"] == "vendor"
assert d["extracted"][0]["bytes"] > 0
PY

# --------------------------------------------------------------------------
head_ "9. consumer: tree builder writes makefiles"
# --------------------------------------------------------------------------
python3 "$ROOT/scripts/make_vendor_tree.py" \
    --manifest "$TMP/man/manifest.json" --root "$TMP/man" \
    --device "$ROOT/firmware/device.json" --mode images >/dev/null 2>&1 \
    && ok "make_vendor_tree ran" || bad "make_vendor_tree failed"

for f in vendor.mk BoardConfigVendor.mk Android.bp README.md; do
    [[ -s "$TMP/man/$f" ]] && ok "$f generated" || bad "$f missing"
done
grep -q "ruan" "$TMP/man/vendor.mk" && ok "vendor.mk names the codename" || bad "vendor.mk content"

# --------------------------------------------------------------------------
head_ "10. integrity helper rejects a bad checksum"
# --------------------------------------------------------------------------
source "$ROOT/scripts/lib.sh"
GOOD="$(clyra_sha256 "$TMP/raw/super.img")"
if ( clyra_verify_sha256 "$TMP/raw/super.img" "$GOOD" test ) >/dev/null 2>&1; then
    ok "correct sha256 accepted"
else
    bad "correct sha256 rejected"
fi
if ( clyra_verify_sha256 "$TMP/raw/super.img" "deadbeef" test ) >/dev/null 2>&1; then
    bad "bad sha256 accepted"
else
    ok "bad sha256 rejected"
fi

# --------------------------------------------------------------------------
head_ "11. device.json is coherent"
# --------------------------------------------------------------------------
python3 - "$ROOT/firmware/device.json" <<'PY' && ok "device.json valid" || bad "device.json invalid"
import json, sys
d = json.load(open(sys.argv[1]))
assert d["codename"] == "ruan"
assert d["hyperos_version"] == "OS3.0.306.0.WFSINXM"
assert d["rom_url"].startswith("https://")
assert d["rom_url"].endswith(d["rom_full_name"] + ".tgz")
assert len(d["rom_url_mirrors"]) >= 2
PY

# --------------------------------------------------------------------------
printf '\n\033[1m%d passed, %d failed\033[0m\n' "$PASS" "$FAIL"
(( FAIL == 0 )) || exit 1
