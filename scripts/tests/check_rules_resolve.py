#!/usr/bin/env python3
"""Every PRODUCT_COPY_FILES source in a vendor.mk must exist on disk.

This is the check that catches the class of bug where the generator emits
`vendor/<codename>/proprietary/...` while the blobs are actually committed at
`proprietary/...`. The makefile parses perfectly and the build then fails (or
silently ships a vendor image with no blobs).

Usage: check_rules_resolve.py <vendor.mk> <repo-root>
"""
import sys
from pathlib import Path


def join_continuations(text: str) -> list[str]:
    out, buf = [], ""
    for line in text.splitlines():
        if line.rstrip().endswith("\\"):
            buf += line.rstrip()[:-1]
        else:
            out.append(buf + line)
            buf = ""
    if buf:
        out.append(buf)
    return out


def sources(mk: Path) -> list[str]:
    found = []
    for line in join_continuations(mk.read_text(encoding="utf-8")):
        if not line.startswith("PRODUCT_COPY_FILES"):
            continue
        rhs = line.split("+=", 1)[1] if "+=" in line else line.split("=", 1)[1]
        for tok in rhs.split():
            if ":" in tok:
                found.append(tok.split(":", 1)[0])
    return found


def main() -> int:
    mk, root = Path(sys.argv[1]), Path(sys.argv[2])
    srcs = sources(mk)
    if not srcs:
        print("no PRODUCT_COPY_FILES rules found", file=sys.stderr)
        return 1

    def present(rel: str) -> bool:
        """A rule is satisfied if the path exists, or is a symlink.

        Vendor trees legitimately contain symlinks whose targets are absolute
        *device* paths (e.g. `/vendor/etc/wifi/...`) that cannot resolve on a
        build host. The link itself is the artifact that gets copied, so
        requiring the target to exist is wrong -- only a genuinely missing
        path is a bug.
        """
        path = root / rel
        return path.exists() or path.is_symlink()

    missing = [s for s in srcs if not present(s)]
    print(f"{len(srcs)} rule(s), {len(missing)} missing source(s)")
    for s in missing[:20]:
        print(f"  MISSING: {s}", file=sys.stderr)

    # Also refuse paths that point into a directory that does not exist at all,
    # which is the fingerprint of the vendor/<codename>/ vs <root> mix-up.
    bogus = [s for s in srcs if s.startswith("vendor/") and not (root / "vendor").is_dir()]
    if bogus:
        print(
            f"  {len(bogus)} rule(s) point into a vendor/ tree that does not exist",
            file=sys.stderr,
        )

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
