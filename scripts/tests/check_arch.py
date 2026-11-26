#!/usr/bin/env python3
"""Enforce a 64-bit-only vendor tree, without destroying coprocessor firmware.

The distinction that matters:

  * **Application CPU code** - anything executed by the SoC's ARM cores:
    binaries in `bin/`, shared objects in `lib64/`, kernel modules, APKs.
    These MUST be AArch64. A stray 32-bit ELF here is a real bug.

  * **Coprocessor firmware** - `vendor/firmware/*`. These are images for the
    Adreno GPU (ZAP shaders) and Hexagon DSP (camera ICP). They are *not*
    ARM code and are never executed by the CPU. Their ELF headers report
    e_machine 94 (Hexagon) or 164 (Qualcomm custom), or ARM32 for the older
    camera firmware. Deleting or "converting" them bricks the camera and GPU.

So: userspace must be 100% AArch64, and firmware is audited separately and
reported rather than rewritten.

Usage: check_arch.py <repo-root> [--strict]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

EM_ARM = 40
EM_AARCH64 = 183
EM_HEXAGON = 164  # Qualcomm: DSP / camera ICP
EM_QCOM_CUSTOM = 94  # Qualcomm: Adreno ZAP

MACHINE_NAMES = {
    EM_ARM: "ARM32 (coprocessor firmware)",
    EM_AARCH64: "AArch64",
    EM_HEXAGON: "Qualcomm Hexagon DSP",
    EM_QCOM_CUSTOM: "Qualcomm custom (Adreno ZAP)",
}

# Directories whose ELF payloads run on the application CPU.
USERSPACE_MARKERS = ("/bin/", "/lib64/", "/app/", "/lib/modules/", "/etc/")


def elf_info(path: Path) -> tuple[int, int, int] | None:
    """(elf_class, e_machine, e_type) or None if not an ELF."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(20)
    except OSError:
        return None
    if len(head) < 20 or head[:4] != b"\x7fELF":
        return None
    return head[4], int.from_bytes(head[18:20], "little"), int.from_bytes(head[16:18], "little")


def is_firmware(rel: str) -> bool:
    return "/firmware/" in rel or rel.startswith("proprietary/firmware/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--strict", action="store_true",
                    help="treat any 32-bit userspace ELF as fatal (default: fatal anyway)")
    args = ap.parse_args()

    root = Path(args.root)
    base = root / "proprietary"
    if not base.is_dir():
        print(f"no proprietary/ tree under {root}", file=sys.stderr)
        return 1

    userspace64 = userspace32 = 0
    fw32: dict[int, int] = {}
    offenders: list[str] = []

    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            p = Path(dirpath) / name
            if p.is_symlink():
                continue
            info = elf_info(p)
            if info is None:
                continue
            elf_class, machine, _etype = info
            rel = str(p.relative_to(root))

            if elf_class == 2:  # 64-bit
                userspace64 += 1
                if machine != EM_AARCH64 and not is_firmware(rel):
                    offenders.append(f"64-bit but not AArch64 ({machine}): {rel}")
                continue

            # 32-bit class
            if is_firmware(rel):
                fw32[machine] = fw32.get(machine, 0) + 1
            else:
                userspace32 += 1
                offenders.append(f"32-bit userspace ELF: {rel}")

    print(f"64-bit ELFs              : {userspace64}")
    print(f"32-bit userspace ELFs    : {userspace32}")
    if fw32:
        print("32-bit coprocessor firmware (expected, kept):")
        for machine, count in sorted(fw32.items()):
            print(f"   {count:3} x {MACHINE_NAMES.get(machine, f'e_machine {machine}')}")

    if offenders:
        print("\nOFFENDERS:", file=sys.stderr)
        for o in offenders[:25]:
            print(f"  {o}", file=sys.stderr)
        return 1

    print("\nOK: userspace is 100% AArch64 (arm64-v8a / x86_64-free).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
