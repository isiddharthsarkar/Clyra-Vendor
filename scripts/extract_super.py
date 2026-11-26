#!/usr/bin/env python3
"""Extract logical partitions out of a `super.img` into a vendor tree.

Two extraction modes are supported:

  * logical  (default)
      Write each requested partition out as a raw image file, e.g.
      `vendor.img` next to `vendor_a.img` if the metadata is slot-suffixed
      (like a vendor blobs repository keeps them).

  * filesystem (`--layout filesystem`)
      Mount-free, root-free unpacking: the image is mounted via loop for
      filesystems the kernel understands (ext4/f2fs) or through `erofsfuse`
      for EROFS, and the *contents* are copied into a directory tree.
      This produces the layout that `vendor/`, `odm/` and friends have in a
      device tree.

The extractor reads the Android `liblp` metadata directly so it works on
plain images as well as Android sparse images, and streams data instead of
materialising intermediates on disk (a `super.img` for a tablet is ~9 GiB).

Usage:
    extract_super.py --super super.img --out-dir DIR [options]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# liblp on-disk constants
# --------------------------------------------------------------------------- #
LP_PARTITION_RESERVED_BYTES = 4096
LP_METADATA_GEOMETRY_MAGIC = 0x616C4467
LP_METADATA_GEOMETRY_SIZE = 4096
LP_METADATA_HEADER_MAGIC = 0x414C5030
LP_SECTOR_SIZE = 512

LP_TARGET_TYPE_LINEAR = 0
LP_TARGET_TYPE_ZERO = 1

SPARSE_HEADER_MAGIC = 0xED26FF3A
SPARSE_CHUNK_HEADER_SIZE = 12
SPARSE_CHUNK_RAW = 0xCAC1
SPARSE_CHUNK_FILL = 0xCAC2
SPARSE_CHUNK_DONT_CARE = 0xCAC3

GEOMETRY_FMT = "<2I32s3I"
HEADER_FMT = "<I2hI32sI32s"
PARTITION_FMT = "<36s4I"
EXTENT_FMT = "<QIQI"


class ExtractError(RuntimeError):
    pass


@dataclass
class Geometry:
    magic: int
    struct_size: int
    checksum: bytes
    metadata_max_size: int
    metadata_slot_count: int
    logical_block_size: int

    @property
    def metadata_region(self) -> int:
        return LP_PARTITION_RESERVED_BYTES + (
            LP_METADATA_GEOMETRY_SIZE + self.metadata_max_size * self.metadata_slot_count
        ) * 2


@dataclass
class Partition:
    name: str
    attributes: int
    first_extent_index: int
    num_extents: int
    group_index: int
    extents: list = field(default_factory=list)

    @property
    def size(self) -> int:
        return sum(e.num_sectors * LP_SECTOR_SIZE for e in self.extents)


@dataclass
class Extent:
    num_sectors: int
    target_type: int
    target_data: int
    target_source: int


def _read_exact(fh, count: int) -> bytes:
    data = fh.read(count)
    if len(data) != count:
        raise ExtractError(f"short read: wanted {count} bytes, got {len(data)}")
    return data


class LpReader:
    """Minimal reader for the Android logical-partition metadata."""

    def __init__(self, path: Path):
        self.path = path
        self.fh = open(path, "rb")
        self._sparse_unpacked: Path | None = None

    # -- sparse handling ---------------------------------------------------- #
    def _is_sparse(self) -> bool:
        pos = self.fh.tell()
        self.fh.seek(0)
        head = self.fh.read(4)
        self.fh.seek(pos)
        return len(head) == 4 and struct.unpack("<I", head)[0] == SPARSE_HEADER_MAGIC

    def unsparse_to(self, dest: Path) -> Path:
        """Expand an Android sparse image into a raw image on disk."""
        self.fh.seek(0)
        (
            magic,
            _major,
            _minor,
            file_hdr_sz,
            chunk_hdr_sz,
            blk_sz,
            total_blks,
            total_chunks,
            _crc,
        ) = struct.unpack("<I4H4I", _read_exact(self.fh, 28))
        if magic != SPARSE_HEADER_MAGIC:
            raise ExtractError("not an Android sparse image")
        self.fh.seek(file_hdr_sz)

        dest.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        with open(dest, "wb") as out:
            for _ in range(total_chunks):
                chunk_type, _res, chunk_sz, total_sz = struct.unpack(
                    "<2H2I", _read_exact(self.fh, SPARSE_CHUNK_HEADER_SIZE)
                )
                if chunk_hdr_sz > SPARSE_CHUNK_HEADER_SIZE:
                    self.fh.seek(chunk_hdr_sz - SPARSE_CHUNK_HEADER_SIZE, os.SEEK_CUR)
                payload = total_sz - chunk_hdr_sz
                nbytes = chunk_sz * blk_sz

                if chunk_type == SPARSE_CHUNK_RAW:
                    remaining = nbytes
                    while remaining:
                        buf = _read_exact(self.fh, min(remaining, 8 << 20))
                        out.write(buf)
                        remaining -= len(buf)
                elif chunk_type == SPARSE_CHUNK_FILL:
                    fill = _read_exact(self.fh, 4)
                    remaining = nbytes
                    while remaining:
                        n = min(remaining, 8 << 20)
                        out.write(fill * (n // 4))
                        remaining -= n
                elif chunk_type == SPARSE_CHUNK_DONT_CARE:
                    out.seek(nbytes, os.SEEK_CUR)
                else:  # CRC32 chunk: no output payload
                    if payload:
                        self.fh.seek(payload, os.SEEK_CUR)
                    continue
                written += nbytes

            expected = total_blks * blk_sz
            if written != expected:
                raise ExtractError(
                    f"sparse expansion size mismatch: wrote {written}, expected {expected}"
                )
            out.truncate(expected)
        self.fh.close()
        self._sparse_unpacked = dest
        return dest

    def reopen(self) -> None:
        self.fh.close()
        self.fh = open(self.path, "rb")

    # -- metadata ----------------------------------------------------------- #
    def _geometry(self) -> tuple[Geometry, int]:
        self.fh.seek(LP_PARTITION_RESERVED_BYTES)
        raw = _read_exact(self.fh, LP_METADATA_GEOMETRY_SIZE)
        geo = Geometry(*struct.unpack(GEOMETRY_FMT, raw[: struct.calcsize(GEOMETRY_FMT)]))
        if geo.magic != LP_METADATA_GEOMETRY_MAGIC:
            raise ExtractError(
                "super.img does not contain valid liblp geometry "
                f"(magic 0x{geo.magic:08x}); is this really a super image?"
            )
        if geo.metadata_slot_count == 0:
            raise ExtractError("liblp geometry declares zero metadata slots")
        return geo, geo.metadata_region

    def _header_layout(self, geo: Geometry) -> tuple[int, dict]:
        base = LP_PARTITION_RESERVED_BYTES + LP_METADATA_GEOMETRY_SIZE * 2
        candidates = []
        for slot in range(geo.metadata_slot_count):
            primary = base + geo.metadata_max_size * slot
            backup = base + geo.metadata_max_size * geo.metadata_slot_count + geo.metadata_max_size * slot
            candidates.extend([primary, backup])

        hdr_size = struct.calcsize(HEADER_FMT)
        desc_size = 12
        for offset in candidates:
            self.fh.seek(offset)
            raw = self.fh.read(hdr_size)
            if len(raw) < hdr_size:
                continue
            (magic, _maj, _min, header_size, _hcrc, tables_size, _tcrc) = struct.unpack(
                HEADER_FMT, raw
            )
            if magic != LP_METADATA_HEADER_MAGIC:
                continue

            # In liblp the four table descriptors are members of the 256-byte
            # header struct itself (offsets 80..128), directly after the
            # 80-byte fixed portion -- *not* after |header_size|.
            self.fh.seek(offset + hdr_size)
            desc = {}
            for key in ("partitions", "extents", "groups", "block_devices"):
                d_off, d_num, d_size = struct.unpack("<3I", _read_exact(self.fh, desc_size))
                desc[key] = (d_off, d_num, d_size)
            return offset, {"header_size": header_size, "tables_size": tables_size, "desc": desc}

        raise ExtractError("no valid liblp metadata header found in primary or backup slots")

    def read_metadata(self) -> list[Partition]:
        geo, _region = self._geometry()
        offset, layout = self._header_layout(geo)
        tables_start = offset + layout["header_size"]

        def table(name: str) -> list[bytes]:
            t_off, t_num, t_size = layout["desc"][name]
            self.fh.seek(tables_start + t_off)
            blob = _read_exact(self.fh, t_num * t_size)
            return [blob[i * t_size : (i + 1) * t_size] for i in range(t_num)]

        full_extents = [Extent(*struct.unpack(EXTENT_FMT, e[: struct.calcsize(EXTENT_FMT)]))
                        for e in table("extents")]

        partitions = []
        for raw in table("partitions"):
            name, attrs, first, num, group = struct.unpack(
                PARTITION_FMT, raw[: struct.calcsize(PARTITION_FMT)]
            )
            part = Partition(
                name=name.rstrip(b"\x00").decode("utf-8", "replace"),
                attributes=attrs,
                first_extent_index=first,
                num_extents=num,
                group_index=group,
            )
            part.extents = full_extents[first : first + num]
            partitions.append(part)

        self.geometry = geo
        self.block_device_size = None
        return partitions

    # -- extraction --------------------------------------------------------- #
    def stream_partition(self, part: Partition, out_path: Path) -> int:
        """Copy a partition's extents into `out_path`, streaming, no temp copy.

        The image is written to a sibling `.partial` file and only renamed into
        place once the full expected size has landed. A short write (ENOSPC, a
        broken pipe, an interrupted run) therefore can never leave a truncated
        `vendor.img` behind for a later step to publish as if it were complete.
        """
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = out_path.with_name(out_path.name + ".partial")
        expected = part.size
        written = 0

        try:
            with open(tmp_path, "wb") as out:
                for ext in part.extents:
                    if ext.target_type == LP_TARGET_TYPE_ZERO:
                        remaining = ext.num_sectors * LP_SECTOR_SIZE
                        zero = b"\x00" * (1 << 20)
                        while remaining:
                            n = min(remaining, 1 << 20)
                            out.write(zero[:n])
                            remaining -= n
                            written += n
                        continue
                    if ext.target_type != LP_TARGET_TYPE_LINEAR:
                        raise ExtractError(
                            f"partition {part.name}: unsupported extent target "
                            f"type {ext.target_type}"
                        )

                    remaining = ext.num_sectors * LP_SECTOR_SIZE
                    self.fh.seek(ext.target_data * LP_SECTOR_SIZE)
                    while remaining:
                        buf = self.fh.read(min(remaining, 8 << 20))
                        if not buf:
                            raise ExtractError(
                                f"partition {part.name}: super.img ended "
                                f"mid-extent ({remaining} bytes short)"
                            )
                        out.write(buf)
                        remaining -= len(buf)
                        written += len(buf)

            if written != expected:
                raise ExtractError(
                    f"partition {part.name}: wrote {written} bytes, "
                    f"expected {expected}"
                )
            out_path.unlink(missing_ok=True)
            tmp_path.rename(out_path)
        except OSError as exc:
            tmp_path.unlink(missing_ok=True)
            raise ExtractError(
                f"partition {part.name}: could not write {out_path}: {exc}\n"
                f"  needed {_human_size(expected)} for this partition alone; "
                f"free space before starting: {_free_space(out_path)}"
            ) from exc
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

        return written

    def close(self) -> None:
        # Closing a read-only handle failing is not actionable; ignore it.
        with contextlib.suppress(OSError):
            self.fh.close()



def _human_size(num: int) -> str:
    value = float(num)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{num} B"


def _free_space(path: Path) -> str:
    """Free space on the filesystem holding `path`, best effort."""
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        return _human_size(shutil.disk_usage(probe).free)
    except OSError:
        return "unknown"


# --------------------------------------------------------------------------- #
# filesystem layout helper
# --------------------------------------------------------------------------- #
def _run(cmd: list[str]) -> None:
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
    )
    if proc.returncode != 0:
        raise ExtractError(f"command failed: {' '.join(cmd)}\n{proc.stdout}")


def _detect_fs(img: Path) -> str | None:
    with open(img, "rb") as fh:
        head = fh.read(2048 + 2)
    if len(head) >= 1082 and head[1080:1082] == b"\x53\xef":
        return "ext4"
    if len(head) < 1024 + 4:
        return None
    if head[1024:1028] == b"\x10\x20\xf5\xf2":
        return "f2fs"
    if head[1024:1028] == b"\xe2\xe1\xf5\xe0":
        return "erofs"
    return None


def _copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for entry in os.scandir(src):
        target = dst / entry.name
        if entry.is_symlink():
            if target.is_symlink() or target.exists():
                target.unlink()
            os.symlink(os.readlink(entry.path), target)
        elif entry.is_dir():
            _copy_tree(Path(entry.path), target)
        elif entry.is_file():
            shutil.copy2(entry.path, target)


def extract_filesystem(img: Path, dst: Path, label: str) -> None:
    fs = _detect_fs(img)
    if fs is None:
        raise ExtractError(f"{label}: unrecognised filesystem, cannot unpack to a tree")

    dst.mkdir(parents=True, exist_ok=True)
    if fs in ("ext4", "f2fs"):
        with tempfile.TemporaryDirectory(prefix="clyra-loop-") as tmp:
            mnt = Path(tmp)
            _run(["sudo", "-n", "mount", "-o", "loop,ro", str(img), str(mnt)])
            try:
                _copy_tree(mnt, dst)
            finally:
                _run(["sudo", "-n", "umount", str(mnt)])
        return

    # EROFS: userspace, no root required.
    if shutil.which("erofsfuse") is None:
        raise ExtractError(
            f"{label}: EROFS image found but `erofsfuse` is not installed.\n"
            "  Debian/Ubuntu: sudo apt-get install erofs-utils\n"
            "  or use --layout logical to keep raw images instead."
        )
    with tempfile.TemporaryDirectory(prefix="clyra-erofs-") as tmp:
        mnt = Path(tmp)
        _run(["erofsfuse", str(img), str(mnt)])
        try:
            _copy_tree(mnt, dst)
        finally:
            subprocess.run(["fusermount", "-u", str(mnt)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)
            subprocess.run(["umount", str(mnt)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--super", required=True, type=Path, help="path to super.img")
    ap.add_argument("--out-dir", required=True, type=Path, help="output directory")
    ap.add_argument("--partitions", default="", help="comma separated partition names")
    ap.add_argument("--layout", choices=("logical", "filesystem"), default="logical")
    ap.add_argument("--keep-images", action="store_true",
                    help="filesystem layout: also keep the raw .img files")
    ap.add_argument("--slots", default="a",
                    help="for slot-suffixed metadata, which slot to take: a, b, or a,b (default: a)")
    ap.add_argument("--list", action="store_true", help="only print the partition table")
    ap.add_argument("--manifest", type=Path, default=None,
                    help="write a JSON manifest of extracted partitions")
    ap.add_argument("--scratch", type=Path, default=None,
                    help="directory for intermediates (defaults to out-dir/.scratch)")
    args = ap.parse_args()

    if not args.super.is_file():
        raise ExtractError(f"super image not found: {args.super}")

    scratch = args.scratch or (args.out_dir / ".scratch")
    scratch.mkdir(parents=True, exist_ok=True)

    reader = LpReader(args.super)
    sparse_tmp = None
    if reader._is_sparse():
        print(f"[super] expanding sparse image {args.super.name} ...", flush=True)
        sparse_tmp = reader.unsparse_to(scratch / (args.super.stem + ".unsparse.img"))
        reader.path = sparse_tmp
        reader.reopen()
        reader._sparse_unpacked = sparse_tmp
        print(f"[super] expanded to {sparse_tmp} "
              f"({sparse_tmp.stat().st_size / (1 << 30):.2f} GiB)", flush=True)

    try:
        partitions = reader.read_metadata()
        by_name = {p.name: p for p in partitions}

        if args.list:
            print(json.dumps(
                [
                    {
                        "name": p.name,
                        "size": p.size,
                        "size_human": f"{p.size / (1 << 20):.1f} MiB",
                        "extents": len(p.extents),
                    }
                    for p in partitions
                ],
                indent=2,
            ))
            return 0

        wanted = [n.strip() for n in args.partitions.split(",") if n.strip()]
        if not wanted:
            wanted = [p.name for p in partitions]

        # Slot-suffixed metadata: `vendor_a` exists but `vendor` was asked for.
        # Preferred slot(s) come first, so a partial run stays small.
        slots = [s.strip() for s in args.slots.split(",") if s.strip()] or ["a"]
        resolved: list[tuple[str, Partition]] = []
        missing: list[str] = []
        for name in wanted:
            if name in by_name:
                resolved.append((name, by_name[name]))
                continue
            candidates = [f"{name}_{s}" for s in slots]
            candidates = [n for n in candidates if n in by_name]
            if candidates:
                for cand in candidates:
                    resolved.append((cand, by_name[cand]))
            else:
                missing.append(name)

        for name in missing:
            print(f"[super] ! requested partition not present: {name}", file=sys.stderr)

        if not resolved:
            raise ExtractError(
                "none of the requested partitions exist in super.img. "
                "Run with --list to inspect the partition table."
            )

        args.out_dir.mkdir(parents=True, exist_ok=True)

        # Pre-flight: refuse to start a long extraction that cannot fit.
        planned = sum(p.size for _, p in resolved)
        free = shutil.disk_usage(args.out_dir).free
        if planned > free:
            raise ExtractError(
                f"not enough free space in {args.out_dir}\n"
                f"  need  : {_human_size(planned)} for {len(resolved)} partition(s)\n"
                f"  free  : {_human_size(free)}\n"
                "Free some space, or extract fewer partitions with "
                "--partitions / firmware/vendor_list_ruan.txt."
            )
        print(
            f"[super] plan: {len(resolved)} partition(s), "
            f"{_human_size(planned)} total, {_human_size(free)} free",
            flush=True,
        )

        manifest = {
            "super": str(args.super),
            "layout": args.layout,
            "logical_block_size": reader.geometry.logical_block_size,
            "metadata_slot_count": reader.geometry.metadata_slot_count,
            "extracted": [],
            "missing": missing,
        }

        for part_name, part in resolved:
            image_path = args.out_dir / f"{part_name}.img"
            print(f"[super] extracting {part_name} ({part.size / (1 << 20):.1f} MiB) ...",
                  flush=True)
            size = reader.stream_partition(part, image_path)
            entry = {
                "partition": part_name,
                "image": image_path.name,
                "bytes": size,
                "extents": len(part.extents),
            }

            if args.layout == "filesystem":
                tree = args.out_dir / part_name
                print(f"[super] unpacking {part_name} -> {tree.name}/ ...", flush=True)
                extract_filesystem(image_path, tree, part_name)
                entry["tree"] = str(tree.relative_to(args.out_dir))
                if not args.keep_images:
                    image_path.unlink()
                    entry["image"] = None
            manifest["extracted"].append(entry)

        if args.manifest:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        print(f"[super] done: {len(resolved)} partition(s) -> {args.out_dir}", flush=True)
    finally:
        reader.close()
        if sparse_tmp and sparse_tmp.exists() and not os.environ.get("CLYRA_KEEP_SCRATCH"):
            sparse_tmp.unlink()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ExtractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        # Bad --out-dir (a file, a read-only mount, ENOSPC).
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)
