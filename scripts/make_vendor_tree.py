#!/usr/bin/env python3
"""Turn raw partition images into a device-tree consumable vendor tree.

Output layout (Android 13+ / AOSP device tree conventions):

    vendor/
      proprietary/
        vendor/{bin,etc,lib,lib64,...}
        odm/{...}
        system_dlkm/{...}
      vendor.mk
      BoardConfigVendor.mk
      Android.bp
      README.md

`vendor.mk` and `BoardConfigVendor.mk` are generated from the files that are
actually present, so they never reference blobs that were not extracted.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Partitions that get a `PRODUCT_COPY_FILES`-style rules file, and how their
# tree maps to the target partition.
PARTITION_TARGETS = {
    "vendor": ("/vendor", "PRODUCT_COPY_FILES"),
    "vendor_dlkm": ("/vendor_dlkm", "PRODUCT_COPY_FILES"),
    "odm": ("/odm", "PRODUCT_COPY_FILES"),
    "odm_dlkm": ("/odm_dlkm", "PRODUCT_COPY_FILES"),
    "system_dlkm": ("/system_dlkm", "PRODUCT_COPY_FILES"),
    "my_product": ("/my_product", "PRODUCT_COPY_FILES"),
    "my_heytap": ("/my_heytap", "PRODUCT_COPY_FILES"),
    "my_manifest": ("/my_manifest", "PRODUCT_COPY_FILES"),
}

# Files that must keep their mode/symlink semantics but are noise in git.
SKIP_NAMES = {"lost+found"}
SKIP_DIRS = {"lost+found"}


def log(msg: str) -> None:
    print(f"[tree] {msg}", flush=True)


class TreeError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# extracting filesystem images without root, via pure-python where possible
# --------------------------------------------------------------------------- #
def _detect_fs(img: Path) -> str | None:
    with open(img, "rb") as fh:
        head = fh.read(4096)
    if len(head) >= 1082 and head[1080:1082] == b"\x53\xef":
        return "ext4"
    if len(head) >= 1028:
        if head[1024:1028] == b"\x10\x20\xf5\xf2":
            return "f2fs"
        if head[1024:1028] == b"\xe2\xe1\xf5\xe0":
            return "erofs"
    return None


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
    )
    if check and proc.returncode != 0:
        raise TreeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}")
    return proc


def _copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for entry in os.scandir(src):
        if entry.name in SKIP_NAMES:
            continue
        target = dst / entry.name
        if entry.is_symlink():
            if target.is_symlink() or target.exists():
                target.unlink()
            os.symlink(os.readlink(entry.path), target)
        elif entry.is_dir():
            if entry.name in SKIP_DIRS:
                continue
            _copy_tree(Path(entry.path), target)
        elif entry.is_file():
            shutil.copy2(entry.path, target)


def unpack_image(img: Path, dst: Path) -> None:
    fs = _detect_fs(img)
    if fs is None:
        raise TreeError(f"{img.name}: unrecognised filesystem")

    dst.mkdir(parents=True, exist_ok=True)

    if fs in ("ext4", "f2fs"):
        with tempfile.TemporaryDirectory(prefix="clyra-mnt-") as tmp:
            mnt = Path(tmp)
            _run(["sudo", "-n", "mount", "-o", "loop,ro", str(img), str(mnt)])
            try:
                _copy_tree(mnt, dst)
            finally:
                _run(["sudo", "-n", "umount", str(mnt)], check=False)
        return

    if shutil.which("erofsfuse"):
        with tempfile.TemporaryDirectory(prefix="clyra-mnt-") as tmp:
            mnt = Path(tmp)
            _run(["erofsfuse", str(img), str(mnt)])
            try:
                _copy_tree(mnt, dst)
            finally:
                _run(["fusermount", "-u", str(mnt)], check=False)
                _run(["umount", str(mnt)], check=False)
        return

    raise TreeError(
        f"{img.name}: EROFS image needs `erofsfuse` "
        "(apt-get install erofs-utils) or --mode images"
    )


# --------------------------------------------------------------------------- #
# prop -> make variable-style rules
# --------------------------------------------------------------------------- #
def quote(text: str) -> str:
    return text.replace("$", "$$").replace(" ", r"\ ")


def walk_files(root: Path) -> list[Path]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            out.append(Path(dirpath) / name)
    return out


def generate_makefile(root: Path, staging: Path, device: dict) -> str:
    """Emit a vendor.mk that is valid AOSP/GNU make.

    Two things this must get right, both of which have bitten before:

    1. PRODUCT_COPY_FILES sources are resolved relative to the *repo root*.
       The blobs live in `<root>/proprietary/...`, so the rule must say
       `proprietary/...` -- not `vendor/<codename>/proprietary/...`, which is
       where they sit in a full device tree but not in this repository.
    2. A comment may never appear inside a `+= \` continuation. GNU make
       treats it as the end of the logical line and silently discards the
       whole list, leaving a makefile that parses but copies nothing.
    """
    entries: dict[str, list[str]] = {}
    empty: list[str] = []
    for dirpath, dirnames, filenames in os.walk(staging):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            src = Path(dirpath) / name
            # Symlinks are real artifacts here, including ones whose target is
            # an absolute *device* path (e.g. /vendor/etc/wifi/...) that can
            # never resolve on a build host. Never skip those.
            if not src.is_symlink() and not src.exists():
                continue
            if not src.is_symlink() and src.stat().st_size == 0:
                empty.append(src.relative_to(staging).as_posix())
            rel = src.relative_to(staging)
            top = rel.parts[0]
            if top not in PARTITION_TARGETS:
                continue
            inner = Path(*rel.parts[1:])
            if not inner.parts:
                continue
            out_var = f"TARGET_COPY_OUT_{_copy_out_name(top)}"
            # Source path as make will resolve it: relative to the repo root.
            try:
                src_rel = src.relative_to(staging.parent).as_posix()
            except ValueError:
                src_rel = rel.as_posix()
            entries.setdefault(out_var, []).append(
                f"    {quote(src_rel)}:$({out_var})/{quote(inner.as_posix())}"
            )

    lines = [
        "# Automatically generated by Clyra-Vendor \u2014 do not edit.",
        f"# Device : {device['device_name']} ({device['codename']})",
        f"# Firmware: {device['hyperos_version']} / Android {device['android_version']}",
        f"# Source : {device['rom_url']}",
        "# Layout : blobs are committed at <repo-root>/proprietary/",
        "",
        "PRODUCT_SOONG_NAMESPACES += \\",
        "    proprietary",
        "",
    ]

    for out_var in sorted(entries):
        lines.append("PRODUCT_COPY_FILES += \\")
        lines.append(" \\\n".join(entries[out_var]))
        lines.append("")

    if not entries:
        lines.append("# No blobs matched a known partition; nothing to copy.")
        lines.append("")

    if empty:
        lines.append("# WARNING: these blobs are 0 bytes and will be copied as-is.")
        for e in empty[:50]:
            lines.append(f"#   0-byte: {e}")
        if len(empty) > 50:
            lines.append(f"#   ... and {len(empty) - 50} more")
        lines.append("")

    if entries:
        lines.append("# Partition output variables used above")
        for out_var in sorted(entries):
            lines.append(f"{out_var} := {_copy_out_path(out_var)}")
        lines.append("")

    return "\n".join(lines)


def _copy_out_path(out_var: str) -> str:
    """`TARGET_COPY_OUT_VENDOR_DLKM` -> `vendor_dlkm`."""
    return out_var.removeprefix("TARGET_COPY_OUT_").lower()


def _copy_out_name(partition: str) -> str:
    return {
        "vendor": "VENDOR",
        "odm": "ODM",
        "vendor_dlkm": "VENDOR_DLKM",
        "odm_dlkm": "ODM_DLKM",
        "system_dlkm": "SYSTEM_DLKM",
        "my_product": "PRODUCT",
        "my_heytap": "PRODUCT",
        "my_manifest": "PRODUCT",
    }.get(partition, "VENDOR")


def generate_boardconfig(staging: Path, device: dict) -> str:
    present = sorted(p.name for p in staging.iterdir() if p.is_dir())
    lines = [
        "# Automatically generated by Clyra-Vendor — do not edit.",
        f"# {device['device_name']} ({device['codename']})",
        "",
    ]
    for part in present:
        if part in ("vendor", "vendor_dlkm"):
            lines.append(r"TARGET_COPY_OUT_VENDOR := vendor")
        break

    lines += [
        "",
        "# Blob source",
        f'BOARD_VENDOR_IMAGE_SOURCE := "{device["rom_full_name"]}"',
        f'BOARD_VENDOR_BLOB_REGION := "{device["region"]}"',
        "",
    ]
    return "\n".join(lines)


def generate_bp(device: dict) -> str:
    return f"""// Automatically generated by Clyra-Vendor — do not edit.
soong_namespace {{
}}

// {device['device_name']} ({device['codename']}), {device['hyperos_version']}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--root", required=True, type=Path, help="directory with extracted images")
    ap.add_argument("--device", required=True, type=Path)
    ap.add_argument("--mode", choices=("images", "tree", "both"), default="images")
    ap.add_argument("--blob-source", default="")
    args = ap.parse_args()

    device = json.loads(args.device.read_text(encoding="utf-8"))
    # Validate the manifest so a malformed one fails loudly; the rules
    # themselves come from the files on disk.
    if args.manifest.exists():
        json.loads(args.manifest.read_text(encoding="utf-8"))

    staging = args.root / "proprietary"
    staging.mkdir(parents=True, exist_ok=True)

    images = sorted(args.root.glob("*.img"))
    if not images:
        log("no partition images found; nothing to stage")
        return 0

    for img in images:
        part = img.stem
        target = staging / part
        if args.mode == "images":
            log(f"keeping {img.name} as a raw image")
            continue
        log(f"unpacking {img.name} -> proprietary/{part}/")
        try:
            unpack_image(img, target)
        except TreeError as exc:
            print(f"[tree] ! {exc}", file=sys.stderr)
            if args.mode == "both":
                continue
            return 1
        if args.mode == "tree":
            img.unlink()

    (args.root / "vendor.mk").write_text(generate_makefile(args.root, staging, device), encoding="utf-8")
    (args.root / "BoardConfigVendor.mk").write_text(generate_boardconfig(args.root, device), encoding="utf-8")
    (args.root / "Android.bp").write_text(generate_bp(device), encoding="utf-8")

    readme = f"""# vendor/{device['codename']} — proprietary blobs

Extracted from the official firmware:

| | |
|---|---|
| Device | {device['device_name']} |
| Codename | `{device['codename']}` |
| Region | {device['market']} (`{device['region']}`) |
| Firmware | `{device['hyperos_version']}` |
| Android | {device['android_version']} |
| Archive | `{device['rom_full_name']}.tgz` |
| Source | {args.blob_source or device['rom_url']} |

Generated by [Clyra-Vendor](../../README.md). Regenerate with:

```bash
./scripts/extract-vendor.sh
```
"""
    (args.root / "README.md").write_text(readme, encoding="utf-8")

    log("wrote vendor.mk, BoardConfigVendor.mk, Android.bp, README.md")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except TreeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
