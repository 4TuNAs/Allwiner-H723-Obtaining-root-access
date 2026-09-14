#!/usr/bin/env python3
"""Inspect Android boot image v3/v4 metadata and common Magisk markers."""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path


def inspect(path: Path) -> dict:
    data = path.read_bytes()
    if data[:8] != b"ANDROID!":
        raise ValueError(f"{path}: ANDROID! magic not found")
    result = {
        "file": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "kernel_size": struct.unpack_from("<I", data, 8)[0],
        "ramdisk_size": struct.unpack_from("<I", data, 12)[0],
        "os_version_field": f"0x{struct.unpack_from('<I', data, 16)[0]:08x}",
        "header_size": struct.unpack_from("<I", data, 20)[0],
        "header_version": struct.unpack_from("<I", data, 40)[0],
        "magisk_markers": {},
    }
    for marker in (b"/.magisk", b"PREINITDEVICE=", b"init-ld.xz"):
        result["magisk_markers"][marker.decode("ascii")] = data.find(marker)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    args = ap.parse_args()
    for name in args.images:
        r = inspect(Path(name))
        print(f"{r['file']}:")
        print(f"  size:           {r['size']}")
        print(f"  SHA-256:        {r['sha256']}")
        print(f"  header version: {r['header_version']}")
        print(f"  header size:    {r['header_size']}")
        print(f"  kernel size:    {r['kernel_size']}")
        print(f"  ramdisk size:   {r['ramdisk_size']}")
        for marker, offset in r["magisk_markers"].items():
            print(f"  {marker:16} {'absent' if offset < 0 else f'offset {offset}'}")
        print()


if __name__ == "__main__":
    main()
