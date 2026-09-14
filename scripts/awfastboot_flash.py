#!/usr/bin/env python3
"""Minimal hash-gated Allwinner USB fastboot flasher used for init_boot_a.

Dry-run by default. Actual flashing requires --yes and an explicit expected
SHA-256. No reboot command is ever sent automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import re

import usb.core
import usb.util


def sha_arg(value: str) -> str:
    value = value.lower().strip()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise argparse.ArgumentTypeError("SHA-256 must be 64 hex characters")
    return value


def int_auto(value: str) -> int:
    return int(value, 0)


def recv_status(dev, ep_in, timeout: int = 10000) -> str:
    while True:
        raw = bytes(dev.read(ep_in, 4096, timeout=timeout))
        text = raw.decode("ascii", errors="replace")
        print("<", repr(text))
        if text.startswith("INFO"):
            continue
        return text


def command(dev, ep_out, ep_in, text: str, timeout: int = 10000) -> str:
    print(">", text)
    dev.write(ep_out, text.encode("ascii"), timeout=timeout)
    return recv_status(dev, ep_in, timeout)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--partition", default="init_boot_a")
    ap.add_argument("--sha256", required=True, type=sha_arg)
    ap.add_argument("--size", type=int, help="Expected image size in bytes")
    ap.add_argument("--vid", type=int_auto, default=0x1F3A)
    ap.add_argument("--pid", type=int_auto, default=0x1010)
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.partition):
        raise SystemExit("Invalid partition name")

    data = open(args.image, "rb").read()
    actual_sha = hashlib.sha256(data).hexdigest()
    print(f"Image size: {len(data)}")
    print(f"SHA-256:    {actual_sha}")
    if actual_sha != args.sha256:
        raise SystemExit("REFUSE: image SHA-256 does not match --sha256")
    if args.size is not None and len(data) != args.size:
        raise SystemExit(f"REFUSE: image size {len(data)} != expected {args.size}")

    dev = usb.core.find(idVendor=args.vid, idProduct=args.pid)
    if dev is None:
        raise SystemExit(f"USB device {args.vid:04x}:{args.pid:04x} not found")
    try:
        dev.set_configuration()
    except usb.core.USBError:
        pass

    cfg = dev.get_active_configuration()
    intf = None
    ep_out = ep_in = None
    for candidate in cfg:
        if (candidate.bInterfaceClass, candidate.bInterfaceSubClass, candidate.bInterfaceProtocol) == (0xFF, 0x42, 0x03):
            intf = candidate
            for ep in candidate:
                if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                    ep_out = ep.bEndpointAddress
                else:
                    ep_in = ep.bEndpointAddress
            break
    if intf is None or ep_out is None or ep_in is None:
        raise SystemExit("Allwinner fastboot interface ff/42/03 not found")

    try:
        try:
            if dev.is_kernel_driver_active(intf.bInterfaceNumber):
                dev.detach_kernel_driver(intf.bInterfaceNumber)
        except Exception:
            pass
        usb.util.claim_interface(dev, intf.bInterfaceNumber)

        result = command(dev, ep_out, ep_in, "getvar:max-download-size")
        if not result.startswith("OKAY"):
            raise SystemExit("getvar:max-download-size failed")

        if not args.yes:
            print(f"DRY RUN PASS. Would flash {args.partition}. Nothing was written.")
            return

        size_hex = f"{len(data):08x}"
        print(">", "download:" + size_hex)
        dev.write(ep_out, ("download:" + size_hex).encode("ascii"), timeout=10000)
        result = recv_status(dev, ep_in, 10000)
        if not result.startswith("DATA"):
            raise SystemExit("download request was not accepted")

        sent = 0
        while sent < len(data):
            chunk = data[sent:sent + 1024 * 1024]
            dev.write(ep_out, chunk, timeout=30000)
            sent += len(chunk)
            print(f"\r{sent}/{len(data)}", end="", flush=True)
        print()
        result = recv_status(dev, ep_in, 30000)
        if not result.startswith("OKAY"):
            raise SystemExit("download data stage failed")

        result = command(dev, ep_out, ep_in, "flash:" + args.partition, timeout=120000)
        if not result.startswith("OKAY"):
            raise SystemExit("FLASH FAILED")
        print("FLASH OK. No reboot command was sent.")
    finally:
        try:
            usb.util.release_interface(dev, intf.bInterfaceNumber)
        except Exception:
            pass
        usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
