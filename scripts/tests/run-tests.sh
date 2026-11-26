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
head_ "12. tree integrity & 64-bit architecture verification"
# --------------------------------------------------------------------------
# Delegate to the real checker so the test cannot drift from the generator.
if python3 "$ROOT/scripts/tests/check_rules_resolve.py" \
        "$ROOT/vendor.mk" "$ROOT" >/dev/null 2>&1; then
    ok "vendor.mk rules all resolve on disk"
else
    bad "vendor.mk rules point at missing files"
fi

# Vendor trees legitimately contain symlinks whose targets are absolute
# *device* paths (/vendor/etc/...). Those cannot resolve on a build host and
# are correct; only a broken *relative* link means a blob went missing.
python3 - "$ROOT" <<'PY' && ok "no broken relative symlinks" || bad "broken symlinks found"
import os, sys
root = sys.argv[1]
broken = []
for r, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d != ".git"]
    for name in dirs + files:
        p = os.path.join(r, name)
        if not os.path.islink(p):
            continue
        target = os.readlink(p)
        if os.path.isabs(target):
            continue          # device-absolute, expected
        if not os.path.exists(p):
            broken.append(p)
assert not broken, f"Broken relative symlinks: {broken}"
PY

python3 - "$ROOT" <<'PY' && ok "pure 64-bit architecture (zero 32-bit CPU binaries/libraries)" || bad "32-bit CPU binary/library found"
import os, sys, struct
root = sys.argv[1]
elf32 = []
# Ensure no 32-bit lib directory exists
assert not os.path.exists(os.path.join(root, "proprietary/vendor/lib")), "proprietary/vendor/lib exists"
assert not os.path.exists(os.path.join(root, "proprietary/odm/lib")), "proprietary/odm/lib exists"

for sub in ["bin", "app", "lib64"]:
    for r, dirs, files in os.walk(os.path.join(root, "proprietary/vendor", sub)):
        for f in files:
            p = os.path.join(r, f)
            if not os.path.islink(p) and os.path.isfile(p):
                try:
                    with open(p, "rb") as fh:
                        head = fh.read(20)
                        if head.startswith(b"\x7fELF") and head[4] == 1:
                            e_machine = struct.unpack("<H", head[18:20])[0] if len(head) >= 20 else 0
                            if e_machine == 40:
                                elf32.append(p)
                except Exception:
                    pass
assert len(elf32) == 0, f"32-bit CPU ELF files: {elf32}"
PY

python3 - "$ROOT" <<'PY' && ok "all active init services reference existing binaries" || bad "missing init binary"
import os, sys, glob
root = sys.argv[1]
for rc in glob.glob(os.path.join(root, "proprietary/**/*.rc"), recursive=True):
    with open(rc, "r", errors="ignore") as fh:
        lines = fh.readlines()
        for idx, line in enumerate(lines):
            l = line.strip()
            if l.startswith("service ") and not l.startswith("#"):
                parts = l.split()
                if len(parts) >= 3:
                    sname, sbin = parts[1], parts[2]
                    disabled = False
                    j = idx + 1
                    while j < len(lines) and (lines[j].startswith(" ") or lines[j].startswith("\t") or lines[j].strip() == ""):
                        if lines[j].strip() == "disabled":
                            disabled = True
                        j += 1
                    if not disabled and sbin.startswith(("/vendor/", "/odm/")):
                        rel = os.path.join(root, "proprietary" + sbin)
                        assert os.path.lexists(rel), f"{rc}: {sname} -> {sbin} missing"
PY

python3 - "$ROOT" <<'PY' && ok "fstab locks removed (no AVB dm-verity or wrappedkey)" || bad "fstab locks present"
import os, sys
root = sys.argv[1]
for fstab in ["proprietary/vendor/etc/fstab.default", "proprietary/vendor/etc/fstab.emmc"]:
    with open(os.path.join(root, fstab)) as fh:
        content = fh.read()
        assert "avb=" not in content, f"AVB found in {fstab}"
        assert "wrappedkey" not in content, f"wrappedkey found in {fstab}"
PY

# --------------------------------------------------------------------------
head_ "16. every generated PRODUCT_COPY_FILES source resolves (regression)"
# --------------------------------------------------------------------------
# The generator used to emit `vendor/<codename>/proprietary/...` while blobs
# were written to `<root>/proprietary/...`. make parsed it fine; every rule
# pointed at a file that did not exist.
mkdir -p "$TMP/res/proprietary/vendor/lib64"
head -c 64 /dev/urandom > "$TMP/res/proprietary/vendor/lib64/libfoo.so"
head -c 64 /dev/urandom > "$TMP/res/vendor.img"

python3 "$ROOT/scripts/make_vendor_tree.py" \
    --manifest "$TMP/res/absent.json" --root "$TMP/res" \
    --device "$ROOT/firmware/device.json" --mode images >/dev/null 2>&1

if python3 "$ROOT/scripts/tests/check_rules_resolve.py" \
        "$TMP/res/vendor.mk" "$TMP/res" >"$TMP/res/check.txt" 2>&1; then
    ok "all PRODUCT_COPY_FILES sources exist on disk"
else
    bad "generated rules point at missing files"
    sed 's/^/      /' "$TMP/res/check.txt" >&2
fi

# --------------------------------------------------------------------------
head_ "17. device-absolute symlinks are kept, broken ones reported"
# --------------------------------------------------------------------------
mkdir -p "$TMP/sym/proprietary/vendor/firmware"
head -c 64 /dev/urandom > "$TMP/sym/vendor.img"
ln -sf /vendor/etc/wifi/qca6490/WCNSS_qcom_cfg.ini \
    "$TMP/sym/proprietary/vendor/firmware/dev_abs.ini"
ln -sf ../../nowhere/missing.so \
    "$TMP/sym/proprietary/vendor/firmware/broken.so"
head -c 64 /dev/urandom > "$TMP/sym/proprietary/vendor/firmware/ok.bin"

python3 "$ROOT/scripts/make_vendor_tree.py" \
    --manifest "$TMP/sym/absent.json" --root "$TMP/sym" \
    --device "$ROOT/firmware/device.json" --mode images >/dev/null 2>&1

if grep -q 'dev_abs.ini' "$TMP/sym/vendor.mk"; then
    ok "device-absolute symlink is referenced (not dropped)"
else
    bad "device-absolute symlink was dropped"
fi

if python3 "$ROOT/scripts/tests/check_blobs.py" "$TMP/sym" >"$TMP/sym/b.txt" 2>&1; then
    bad "check_blobs accepted a broken relative symlink"
else
    ok "check_blobs flags the broken relative symlink"
fi

# --------------------------------------------------------------------------
head_ "18. empty critical blobs are reported"
# --------------------------------------------------------------------------
mkdir -p "$TMP/empty/proprietary/vendor/firmware"
: > "$TMP/empty/proprietary/vendor/firmware/evass.b10"
if python3 "$ROOT/scripts/tests/check_blobs.py" "$TMP/empty" --strict \
        >"$TMP/empty/b.txt" 2>&1; then
    bad "check_blobs --strict accepted a 0-byte firmware blob"
else
    ok "check_blobs --strict rejects a 0-byte firmware blob"
fi


# --------------------------------------------------------------------------
head_ "19. architecture is 64-bit only (regression)"
# --------------------------------------------------------------------------
if python3 "$ROOT/scripts/tests/check_arch.py" "$ROOT" >"$TMP/arch.txt" 2>&1; then
    ok "userspace is 100% AArch64"
else
    bad "32-bit userspace ELF found"
    sed 's/^/      /' "$TMP/arch.txt" >&2
fi

# Coprocessor firmware must be PRESENT and untouched. Deleting these because
# they report a 32-bit ELF header breaks the camera and GPU.
python3 - "$ROOT" <<'PY' && ok "coprocessor firmware preserved (not stripped)" || bad "coprocessor firmware missing"
import os, sys
root = sys.argv[1]
fw = os.path.join(root, "proprietary/vendor/firmware")
need = ["CAMERA_ICP.b00", "a610_zap.b00"]
missing = [n for n in need if not os.path.exists(os.path.join(fw, n))]
assert not missing, f"missing firmware: {missing}"
PY

# No 32-bit ABI may be advertised anywhere.
python3 - "$ROOT" <<'PY' && ok "no 32-bit ABI advertised" || bad "32-bit ABI advertised"
import os, re, sys
root = sys.argv[1]
bad = []
for dp, _, fs in os.walk(os.path.join(root, "proprietary")):
    for f in fs:
        if not f.endswith(".prop"):
            continue
        p = os.path.join(dp, f)
        if os.path.islink(p):
            continue
        for line in open(p, encoding="utf-8", errors="replace"):
            m = re.match(r"\s*([\w.]+abilist32)\s*=\s*(\S+)", line)
            if m and m.group(2):
                bad.append(f"{p}: {line.strip()}")
assert not bad, bad
PY

# --------------------------------------------------------------------------
head_ "20. build files are in sync with targets.json"
# --------------------------------------------------------------------------
if python3 "$ROOT/scripts/generate_build_files.py" --root "$ROOT" --check \
        >"$TMP/gen.txt" 2>&1; then
    ok "generated build files up to date"
else
    bad "generated build files are stale"
    sed 's/^/      /' "$TMP/gen.txt" >&2
fi

# --------------------------------------------------------------------------
head_ "21. cross-port: every SM7435 target builds the same vendor"
# --------------------------------------------------------------------------
for dev in ruan garnet organ flute; do
    n=$(make -s -f - probe 2>/dev/null <<EOF
TARGET_DEVICE := $dev
CLYRA_VENDOR_PATH := .
include vendor-port.mk
probe:
	@echo \$(words \$(PRODUCT_COPY_FILES))
EOF
)
    if [[ "${n:-0}" -gt 0 ]]; then
        ok "$dev resolves $n vendor rules"
    else
        bad "$dev resolved 0 vendor rules"
    fi
done

# A device outside the supported set must be skipped, not broken.
n=$(make -s -f - probe 2>/dev/null <<'EOF'
TARGET_DEVICE := raphael
CLYRA_VENDOR_PATH := .
include vendor-port.mk
probe:
	@echo $(words $(PRODUCT_COPY_FILES))
EOF
)
if [[ "${n:-x}" == "0" ]]; then
    ok "unsupported device skipped cleanly"
else
    bad "unsupported device produced '${n:-error}'"
fi

# --------------------------------------------------------------------------
head_ "22. kernel modules resolve and match modules.load"
# --------------------------------------------------------------------------
if make -s -f - probe 2>&1 <<'EOF' >"$TMP/ko.txt" 2>&1
include BoardConfigVendor.mk
probe:
	@printf "ko=%s\nload=%s\n" "$(words $(BOARD_VENDOR_KERNEL_MODULES))" "$(words $(BOARD_VENDOR_KERNEL_MODULES_LOAD))"
EOF
then ok "BoardConfigVendor.mk evaluates"; else bad "BoardConfigVendor.mk failed to evaluate"; fi

ko=$(grep -oP 'ko=\K[0-9]+' "$TMP/ko.txt" | head -1)
if [[ "${ko:-0}" -gt 0 ]]; then
    ok "kernel modules resolve ($ko found)"
else
    bad "kernel module wildcard expanded to nothing"
fi

# --------------------------------------------------------------------------
printf '\n\033[1m%d passed, %d failed\033[0m\n' "$PASS" "$FAIL"
(( FAIL == 0 )) || exit 1
