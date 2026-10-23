#!/usr/bin/env python3
"""Extract ARM32 patcher from a user-supplied Magisk APK (tested v30.7).

This does not access the network, write any firmware or distribute Magisk.
"""
from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

FILES = {
    "assets/boot_patch.sh": "boot_patch.sh",
    "assets/util_functions.sh": "util_functions.sh",
    "assets/stub.apk": "stub.apk",
    "lib/armeabi-v7a/libbusybox.so": "busybox",
    "lib/armeabi-v7a/libmagisk.so": "magisk",
    "lib/armeabi-v7a/libmagiskboot.so": "magiskboot",
    "lib/armeabi-v7a/libmagiskinit.so": "magiskinit",
    "lib/armeabi-v7a/libinit-ld.so": "init-ld",
}

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("apk", type=Path, help="Locally downloaded official Magisk APK (tested v30.7)")
    ap.add_argument("--out", type=Path, default=Path("mp"))
    args = ap.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        ap.error(f"{args.out} is not empty; rename or remove it first")
    with zipfile.ZipFile(args.apk) as archive:
        missing = [name for name in FILES if name not in archive.namelist()]
        if missing:
            ap.error(f"Missing required APK entries: {missing}")
        args.out.mkdir(parents=True, exist_ok=True)
        for source, filename in FILES.items():
            data = archive.read(source)
            dest = args.out / filename
            dest.write_bytes(data)
            print(f"{dest}: {len(data)} bytes sha256={hashlib.sha256(data).hexdigest()}")
    print("Now run patch_init_boot.cmd, using your own init_boot_a.img.")

if __name__ == "__main__":
    main()
