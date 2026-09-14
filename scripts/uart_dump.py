#!/usr/bin/env python3
"""Strict read-only raw eMMC dumper over the H723 recovery UART shell."""

from __future__ import annotations

import argparse
import base64
import hashlib
import secrets
import time
from pathlib import Path

import serial

SECTOR = 512


def is_base64_line(line: str) -> bool:
    return bool(line) and all(c.isalnum() or c in "+/=" for c in line)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("port", help="UART port, e.g. COM5 or /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--skip", type=int, required=True, help="Starting 512-byte LBA")
    ap.add_argument("--count", type=int, required=True, help="Number of 512-byte sectors")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.skip < 0 or args.count <= 0:
        raise SystemExit("--skip must be >= 0 and --count must be > 0")

    expected = args.count * SECTOR
    token = secrets.token_hex(8)
    begin = f"__H723_BEGIN_{token}__"
    end = f"__H723_END_{token}__"
    command = (
        f"echo {begin}; "
        f"dd if=/dev/block/mmcblk0 bs=512 skip={args.skip} count={args.count} "
        f"2>/dev/null | base64; echo {end}"
    )

    ser = serial.Serial(args.port, args.baud, timeout=0.25, write_timeout=2)
    try:
        try:
            ser.dtr = False
            ser.rts = False
        except Exception:
            pass
        time.sleep(0.3)
        ser.reset_input_buffer()
        ser.write(b"\r\n")
        ser.flush()
        time.sleep(0.2)
        ser.write((command + "\r\n").encode("ascii"))
        ser.flush()

        collecting = False
        payload_lines: list[str] = []
        estimate = expected * 4 / 3 * 10 / max(args.baud, 1)
        deadline = time.time() + max(30, estimate * 4 + 20)

        while time.time() < deadline:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("ascii", errors="ignore").replace("\r", "").replace("\n", "").strip()
            if line == begin:
                collecting = True
                payload_lines.clear()
                continue
            if line == end:
                if not collecting:
                    raise RuntimeError("END marker arrived before BEGIN marker")
                payload = "".join(payload_lines)
                data = base64.b64decode(payload, validate=True)
                if len(data) != expected:
                    raise RuntimeError(f"Dump length mismatch: got {len(data)}, expected {expected}")
                out = Path(args.out)
                out.write_bytes(data)
                print(f"Saved {out} ({len(data)} bytes)")
                print(f"SHA-256: {hashlib.sha256(data).hexdigest()}")
                return
            if collecting:
                if not is_base64_line(line):
                    raise RuntimeError(f"Unexpected non-Base64 line inside payload: {line!r}")
                payload_lines.append(line)

        raise TimeoutError("Timed out waiting for UART dump END marker")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
