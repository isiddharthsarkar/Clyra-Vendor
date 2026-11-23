# Clyra-Vendor

Proprietary blob extraction for **Redmi Pad Pro 5G (`ruan`)** — HyperOS 3 /
Android 16. Feed it a full fastboot ROM; get back a clean vendor tree, ready to
push to GitHub.

| | |
|---|---|
| Device | Redmi Pad Pro 5G (`24074RPD2G`) |
| Codename | `ruan` |
| Region | India (`ruan_in_global`) |
| Firmware | `OS3.0.306.0.WFSINXM` |
| Android | 16.0 |
| ROM archive | `ruan_in_global_images_OS3.0.306.0.WFSINXM_20261021.0000.00_16.0_in_e97cbecd4c.tgz` |

---

## Quick start

```bash
./scripts/extract-vendor.sh          # download ROM → extract vendor → stage tree
./scripts/publish-vendor.sh --dry-run   # preview what will be pushed
./scripts/publish-vendor.sh             # commit + push to the vendor branch
```

Everything is resumable. If a download or a run dies, run it again.

### Already have the ROM?

```bash
./scripts/extract-vendor.sh --from-archive                 # skip the download
./scripts/extract-vendor.sh --super /path/to/super.img     # skip download + unpack
```

---

## What gets extracted

Partitions are listed in [`firmware/vendor_list_ruan.txt`](firmware/vendor_list_ruan.txt)
and are read straight out of `super.img` using the Android `liblp` metadata:

| Partition | Contents |
|---|---|
| `vendor` | HALs, firmware, vendor libs — the bulk of the blobs |
| `vendor_dlkm` | Vendor kernel modules |
| `odm` | Device-specific overlays, configs, props |
| `odm_dlkm` | ODM kernel modules |
| `system_dlkm` | System kernel modules |
| `my_product`, `my_heytap`, `my_manifest` | HyperOS product blobs |

Partitions that are not present on a given firmware are reported and skipped —
the run does not fail.

---

## Output layout

```text
vendor/
├── vendor.img                 # raw logical partition images
├── odm.img                    #   (--layout logical, default)
├── vendor_dlkm.img
├── …                          #   or unpacked trees with --layout filesystem
├── proprietary/
│   ├── vendor/{bin,etc,lib,lib64,…}
│   └── odm/{…}
├── vendor.mk                  # generated PRODUCT_COPY_FILES
├── BoardConfigVendor.mk
├── Android.bp
├── README.md
└── .gitignore                 # regenerated: only partitions that exist
```

`vendor.mk`, `BoardConfigVendor.mk` and `Android.bp` are **generated from what was
actually extracted**, so they never reference a blob that isn't there.

### Two layouts

```bash
./scripts/extract-vendor.sh --layout logical     # default: *.img files
./scripts/extract-vendor.sh --layout filesystem  # unpacked directory trees
```

`logical` is the safer default: it never needs root and preserves the images
bit-for-bit. `filesystem` mounts each image read-only and copies out the
contents — useful for diffing against another firmware, but it needs `sudo`
(ext4/f2fs) and `erofsfuse` (EROFS, `apt install erofs-utils`).

---

## Publishing to GitHub

`publish-vendor.sh` pushes the staged tree to a dedicated branch
(`ruan-in-16.0`, set in `firmware/device.json`) as an **orphan branch**, so
vendor blobs never mix with source code commits.

```bash
./scripts/publish-vendor.sh --repo owner/repo --branch ruan-in-16.0
```

Key behaviours:

- **Size guard.** GitHub hard-blocks any file over 100 MiB and warns above
  50 MiB. Files above `CLYRA_MAX_BLOB` (default 45 MiB) abort the run *before*
  anything is pushed, with the offending paths listed.
- **Chunked commits.** Files are committed in batches limited by both count and
  bytes, pushing after each batch — a failure halfway keeps completed work.
- **Symlinks preserved.** Vendor trees are full of them (`libfoo.so →
  libfoo.so.1`); they are committed as real symlinks, not flattened copies.
- **Resumable.** Re-running continues from the existing branch.

Tuning:

```bash
CLYRA_MAX_BLOB=45 CLYRA_CHUNK_FILES=400 CLYRA_CHUNK_BYTES=1700 \
  ./scripts/publish-vendor.sh
```

---

## Staying under GitHub's limits

A `ruan` vendor set is several GiB across tens of thousands of files. If you hit
push limits, in rough order of preference:

1. **Publish only what you need.** Trim `firmware/vendor_list_ruan.txt` to the
   partitions your build actually consumes (often just `vendor` + `odm`).
2. **Split across branches or repos** — one per partition, e.g.
   `ruan-in-16.0` and `ruan-in-16.0-dlkm`.
3. **Use Git LFS** for the large `.so` files, and raise `CLYRA_MAX_BLOB`.
4. **Use `--layout filesystem`** and drop `lib64` duplicates via symlinks first.

If a partition image is genuinely too large to publish as a file, publishing the
`filesystem` layout usually fits — the image is mostly padding and duplicate
symlink targets that collapse once unpacked.

---

## Integrity

The archive is SHA-256 verified before anything is extracted
(`clyra_verify_sha256`, `scripts/lib.sh`). If `rom_sha256` in
`firmware/device.json` is `"-"` the check is skipped with a warning rather than
silently passing.

---

## Testing

No device, network, or root needed:

```bash
./scripts/tests/run-tests.sh
```

The suite builds real `super.img` fixtures (valid `liblp` geometry, metadata and
extents), then checks the extractor against the vendored upstream `lpunpack` as
an independent oracle — output must be **byte-identical**. It also covers sparse
images, slot-suffixed metadata, missing partitions, the JSON manifest, generated
makefiles, and checksum handling.

---

## Repository layout

```text
firmware/device.json          device + ROM metadata (URLs, mirrors, hashes)
firmware/vendor_list_ruan.txt partitions to extract
scripts/lib.sh                shared helpers (download, sha256, logging)
scripts/extract-vendor.sh     orchestrator: download → unpack → extract → stage
scripts/extract_super.py      streaming liblp extractor (+ sparse support)
scripts/make_vendor_tree.py   device-tree consumer: makefiles, layout
scripts/publish-vendor.sh     chunked, guarded GitHub publisher
scripts/tests/                fixture generator + self-test suite
tools/vendor/lpunpack.py      upstream oracle (LGPL-3.0, pinned)
```

---

## Debugging a firmware

Inspect a `super.img` without extracting anything:

```bash
python3 scripts/extract_super.py --super super.img --out-dir /tmp/x --list
```

Not sure whether a partition is there?

```bash
python3 scripts/extract_super.py --super super.img --out-dir /tmp/x --list \
  | python3 -c 'import json,sys; print("\n".join(p["name"] for p in json.load(sys.stdin)))'
```

---

## Notes & limits

- **ext4/f2fs trees need root** to mount; `sudo -n` is used, so it must be
  passwordless, or use `--layout logical` instead.
- **EROFS needs `erofsfuse`** for tree extraction. Raw images need neither.
- **No deodexing / no patching.** This extracts blobs exactly as shipped. The
  binaries are untouched; nothing here modifies a device.
- Blobs are the property of their respective owners. Use them for backups and
  interoperability only.

---

## Credits

- [`unix3dgforce/lpunpack`](https://github.com/unix3dgforce/lpunpack) — vendored
  as an independent test oracle (LGPL-3.0, see
  [`tools/vendor/LICENSE.lpunpack.md`](tools/vendor/LICENSE.lpunpack.md)).
- Android `liblp` metadata format (AOSP `system/core/fs_mgr/liblp`).
