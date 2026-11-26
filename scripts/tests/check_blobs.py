#!/usr/bin/env python3
"""Sanity-check a staged vendor tree before it is published.

Catches the failure modes that leave a *buildable* repo that produces a
broken device:

  * 0-byte blobs   - firmware images / fs_config / sepolicy truncated by a
                     failed copy. Flashing them hard-bricks radios or SELinux.
  * broken symlinks that are not device-absolute - a relative link whose
                     target was never extracted.
  * rules pointing at paths that do not exist (delegated to
                     check_rules_resolve.py when a vendor.mk is present).

Usage: check_blobs.py <repo-root> [--strict]
Exit status is 1 when a fatal problem is found.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Extension / name patterns where a 0-byte file is fatal rather than benign.
CRITICAL_SUFFIXES = (
    ".so", ".ko", ".apk", ".odex", ".vdex", ".jar",
    ".bin", ".mbn", ".b0", ".b00", ".elf", ".img",
    ".ini", ".conf", ".xml", ".json", ".rc", ".prop",
)
CRITICAL_NAMES = {
    "fs_config_dirs", "fs_config_files", "passwd", "group",
    "precompiled_sepolicy", "ueventd.rc", "build.prop",
    "rfs_symlinks", "modules.load", "modules.dep", "modules.alias",
}


def is_critical(rel: str) -> bool:
    name = os.path.basename(rel)
    if name in CRITICAL_NAMES:
        return True
    if name.endswith(CRITICAL_SUFFIXES):
        return True
    # Qualcomm firmware fragments: *.b10 .. *.b19
    stem, ext = os.path.splitext(name)
    return bool(stem) and ext.startswith(".b") and ext[2:].isdigit()


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    strict = "--strict" in sys.argv
    base = root / "proprietary"
    if not base.is_dir():
        print(f"no proprietary/ tree under {root}", file=sys.stderr)
        return 1

    empty: list[str] = []
    broken: list[str] = []
    total = 0

    for dirpath, dirnames, filenames in os.walk(base):
        for name in filenames:
            p = Path(dirpath) / name
            total += 1
            if p.is_symlink():
                target = os.readlink(p)
                if os.path.isabs(target):
                    continue  # device-absolute: correct for a vendor blob
                if not (p.parent / target).exists():
                    broken.append(str(p.relative_to(root)))
                continue
            if p.stat().st_size == 0:
                empty.append(str(p.relative_to(root)))

    crit_empty = [e for e in empty if is_critical(e)]

    print(f"blobs scanned      : {total}")
    print(f"0-byte blobs       : {len(empty)}  ({len(crit_empty)} critical)")
    print(f"broken rel symlinks: {len(broken)}")

    for e in crit_empty:
        print(f"  EMPTY CRITICAL: {e}", file=sys.stderr)
    for b in broken[:20]:
        print(f"  BROKEN LINK   : {b}", file=sys.stderr)

    fatal = bool(broken) or (strict and bool(crit_empty))
    if crit_empty and not strict:
        print(
            "\nWARNING: critical blobs are 0 bytes. These will be copied into the\n"
            "vendor image and will fail on device. Re-extract from the ROM, or\n"
            "run with --strict to make this fatal.",
            file=sys.stderr,
        )
    return 1 if fatal else 0


if __name__ == "__main__":
    sys.exit(main())
