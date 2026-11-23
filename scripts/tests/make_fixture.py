#!/usr/bin/env python3
"""Build a small but *structurally valid* super.img for testing.

This writes real liblp geometry + metadata + extents, so the extraction
pipeline is exercised against the same structures a device super image uses.
Nothing here touches a real device.

    make_fixture.py --out /tmp/fx [--sparse] [--slot-suffix]
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path

LP_PARTITION_RESERVED_BYTES = 4096
LP_METADATA_GEOMETRY_MAGIC = 0x616C4467
LP_METADATA_GEOMETRY_SIZE = 4096
LP_METADATA_HEADER_MAGIC = 0x414C5030
LP_SECTOR_SIZE = 512

SPARSE_HEADER_MAGIC = 0xED26FF3A

GEOMETRY_FMT = "<2I32s3I"
HEADER_FMT = "<I2hI32sI32s"
DESC_FMT = "<3I"
PARTITION_FMT = "<36s4I"
EXTENT_FMT = "<QIQI"
GROUP_FMT = "<36sIQ"
BLOCKDEV_FMT = "<Q2IQ36sI"

HEADER_SIZE = 256
LOGICAL_BLOCK_SIZE = 4096
METADATA_MAX_SIZE = 65536
SLOT_COUNT = 2


def _pad(data: bytes, size: int) -> bytes:
    return data + b"\x00" * (size - len(data))


def build_super(
    out: Path,
    partitions: dict[str, bytes],
    slot_suffix: bool = False,
    sparse: bool = False,
    alignment: int = LOGICAL_BLOCK_SIZE,
) -> Path:
    names = sorted(partitions)

    # ---- lay out extents ------------------------------------------------- #
    extents = []
    cursor = 0
    part_records = []
    for idx, name in enumerate(names):
        payload = partitions[name]
        # pad to logical block size
        padded = payload + b"\x00" * ((alignment - len(payload) % alignment) % alignment)
        sectors = len(padded) // LP_SECTOR_SIZE
        extents.append((sectors, 0, cursor // LP_SECTOR_SIZE, 0))  # linear
        part_records.append(
            (
                (f"{name}{'_a' if slot_suffix else ''}").encode().ljust(36, b"\x00"),
                0,                       # attributes
                idx,                     # first_extent_index
                1,                       # num_extents
                0,                       # group_index
            )
        )
        cursor += len(padded)

    data_region_first_sector = (
        (LP_PARTITION_RESERVED_BYTES
         + (LP_METADATA_GEOMETRY_SIZE + METADATA_MAX_SIZE * SLOT_COUNT) * 2
         + alignment - 1) // alignment
    ) * (alignment // LP_SECTOR_SIZE)
    data_start = data_region_first_sector * LP_SECTOR_SIZE

    # shift extents to sit after the metadata region
    shifted = [(n, t, d + data_region_first_sector, s) for (n, t, d, s) in extents]
    total_data = cursor
    device_size = data_start + total_data

    # ---- tables ---------------------------------------------------------- #
    part_tbl = b"".join(struct.pack(PARTITION_FMT, *r) for r in part_records)

    extent_tbl = b"".join(struct.pack(EXTENT_FMT, *e) for e in shifted)

    group_tbl = struct.pack(GROUP_FMT, b"default".ljust(36, b"\x00"), 0, 0)

    blockdev_tbl = struct.pack(
        BLOCKDEV_FMT,
        data_region_first_sector,
        alignment,
        0,
        device_size,
        b"super".ljust(36, b"\x00"),
        0,
    )

    offsets = {"partitions": 0}
    offsets["extents"] = offsets["partitions"] + len(part_tbl)
    offsets["groups"] = offsets["extents"] + len(extent_tbl)
    offsets["block_devices"] = offsets["groups"] + len(group_tbl)
    tables_size = offsets["block_devices"] + len(blockdev_tbl)

    tables = part_tbl + extent_tbl + group_tbl + blockdev_tbl
    tables_checksum = hashlib.sha256(tables).digest()

    # header, checksum computed with the checksum field zeroed
    header_body = struct.pack(
        HEADER_FMT,
        LP_METADATA_HEADER_MAGIC,
        10,                      # major
        2,                       # minor  (1.2)
        HEADER_SIZE,
        b"\x00" * 32,
        tables_size,
        tables_checksum,
    )
    # header + the four table descriptors embedded in it (they start at
    # offset 80 in the AOSP header and are part of the padded 256-byte struct)
    descs = b"".join(
        struct.pack(DESC_FMT, offsets[k], count, struct.calcsize(fmt))
        for k, count, fmt in (
            ("partitions", len(part_records), PARTITION_FMT),
            ("extents", len(shifted), EXTENT_FMT),
            ("groups", 1, GROUP_FMT),
            ("block_devices", 1, BLOCKDEV_FMT),
        )
    )
    header_struct = _pad(header_body + descs, HEADER_SIZE)
    header_checksum = hashlib.sha256(header_struct).digest()
    header = header_struct[:12] + header_checksum + header_struct[44:]
    metadata = _pad(header + tables, METADATA_MAX_SIZE)

    geometry = struct.pack(
        GEOMETRY_FMT,
        LP_METADATA_GEOMETRY_MAGIC,
        GEOMETRY_FMT and struct.calcsize(GEOMETRY_FMT),
        hashlib.sha256(struct.pack(GEOMETRY_FMT, LP_METADATA_GEOMETRY_MAGIC,
                                   struct.calcsize(GEOMETRY_FMT), b"\x00" * 32,
                                   METADATA_MAX_SIZE, SLOT_COUNT,
                                   LOGICAL_BLOCK_SIZE)).digest(),
        METADATA_MAX_SIZE,
        SLOT_COUNT,
        LOGICAL_BLOCK_SIZE,
    )
    geometry = _pad(geometry, LP_METADATA_GEOMETRY_SIZE)

    # ---- assemble -------------------------------------------------------- #
    primary_geo = LP_PARTITION_RESERVED_BYTES
    backup_geo = primary_geo + LP_METADATA_GEOMETRY_SIZE
    primary_meta = backup_geo + LP_METADATA_GEOMETRY_SIZE
    backup_meta = primary_meta + METADATA_MAX_SIZE * SLOT_COUNT

    blob = bytearray(device_size)
    blob[primary_geo:primary_geo + LP_METADATA_GEOMETRY_SIZE] = geometry
    blob[backup_geo:backup_geo + LP_METADATA_GEOMETRY_SIZE] = geometry
    for slot in range(SLOT_COUNT):
        s = primary_meta + slot * METADATA_MAX_SIZE
        b = backup_meta + slot * METADATA_MAX_SIZE
        blob[s:s + METADATA_MAX_SIZE] = metadata
        blob[b:b + METADATA_MAX_SIZE] = metadata

    # data
    pos = data_start
    for name in names:
        payload = partitions[name]
        padded = payload + b"\x00" * ((alignment - len(payload) % alignment) % alignment)
        blob[pos:pos + len(padded)] = padded
        pos += len(padded)

    out.parent.mkdir(parents=True, exist_ok=True)
    if sparse:
        out.write_bytes(to_sparse(bytes(blob)))
    else:
        out.write_bytes(bytes(blob))
    return out


def to_sparse(data: bytes, blk_sz: int = 4096, chunk_blocks: int = 8) -> bytes:
    """Wrap raw data as an Android sparse image (raw + don't-care chunks)."""
    assert len(data) % blk_sz == 0
    total_blks = len(data) // blk_sz

    chunks = []
    step = chunk_blocks * blk_sz
    for off in range(0, len(data), step):
        chunk = data[off:off + step]
        if chunk.count(0) == len(chunk):
            chunks.append((0xCAC3, blk_sz and len(chunk) // blk_sz, b""))
        else:
            chunks.append((0xCAC1, len(chunk) // blk_sz, chunk))

    out = bytearray()
    hdr = struct.pack(
        "<I4H4I",
        SPARSE_HEADER_MAGIC, 1, 0, 28, 12,
        blk_sz, total_blks, len(chunks), 0,
    )
    out += hdr
    for ctype, cblocks, payload in chunks:
        total_sz = 12 + (4 if ctype == 0xCAC2 else len(payload))
        out += struct.pack("<2H2I", ctype, 0, cblocks, total_sz)
        if ctype == 0xCAC1:
            out += payload
    return bytes(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--sparse", action="store_true")
    ap.add_argument("--slot-suffix", action="store_true")
    ap.add_argument("--names", default="vendor,vendor_dlkm,odm,system_dlkm,my_product")
    args = ap.parse_args()

    parts = {}
    for name in args.names.split(","):
        name = name.strip()
        if not name:
            continue
        # distinctive payload so we can prove the right bytes land in the right file
        body = (f"CLYRA-FIXTURE:{name}\n".encode() * 512)
        parts[name] = body

    path = build_super(args.out, parts, slot_suffix=args.slot_suffix, sparse=args.sparse)
    print(f"wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
