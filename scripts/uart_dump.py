#!/usr/bin/env python3
"""Read-only H723 eMMC dump over recovery UART, with progress and safe cancellation.

A Windows Ctrl+C normally stops only the host script. This version also sends
Ctrl+C to the recovery UART shell and verifies that the shell is responsive.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import secrets
import sys
import time
from pathlib import Path

import serial

SECTOR = 512


def is_base64_line(line: str) -> bool:
    return bool(line) and all(c.isalnum() or c in "+/=" for c in line)


def human_bytes(n: float) -> str:
    value = float(n)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GiB"


def human_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}" if hours else f"{minutes:02}:{secs:02}"


class ProgressBar:
    """Terminal progress bar without extra dependencies."""

    def __init__(self, total: int, enabled: bool, width: int = 30):
        self.total = max(total, 1)
        self.enabled = enabled and sys.stderr.isatty()
        self.width = width
        self.start = time.monotonic()
        self.last_draw = 0.0
        self.drawn = False

    def reset_clock(self) -> None:
        self.start = time.monotonic()
        self.last_draw = 0.0

    def update(self, current: int, force: bool = False) -> None:
        if not self.enabled:
            return
        now = time.monotonic()
        if not force and now - self.last_draw < 0.1:
            return
        self.last_draw = now
        self.drawn = True

        current = min(max(current, 0), self.total)
        frac = current / self.total
        filled = int(frac * self.width)
        if filled >= self.width:
            bar = "=" * self.width
        else:
            bar = "=" * filled + ">" + " " * (self.width - filled - 1)

        elapsed = now - self.start
        rate = current / elapsed if elapsed > 0 else 0.0
        eta = human_time((self.total - current) / rate) if rate > 0 else "--:--"
        sys.stderr.write(
            f"\r[{bar}] {frac * 100:5.1f}%  "
            f"{human_bytes(current)} / {human_bytes(self.total)}  "
            f"{human_bytes(rate)}/s  ETA {eta}"
        )
        sys.stderr.flush()

    def end_line(self) -> None:
        if self.drawn:
            sys.stderr.write("\n")
            sys.stderr.flush()
            self.drawn = False

    def finish(self) -> None:
        self.update(self.total, force=True)
        self.end_line()


def read_line(ser: serial.Serial) -> str:
    return ser.readline().decode("ascii", errors="ignore").strip()


def send_line(ser: serial.Serial, command: str) -> None:
    ser.write((command + "\r\n").encode("ascii"))
    ser.flush()


def wait_for_marker(ser: serial.Serial, marker: str, seconds: float) -> bool:
    """Require marker as a full line (not the terminal's echo of 'echo ...')."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if read_line(ser) == marker:
            return True
    return False


def probe_shell(ser: serial.Serial, seconds: float = 3.0) -> bool:
    marker = f"__H723_READY_{secrets.token_hex(8)}__"
    send_line(ser, f"echo {marker}")
    return wait_for_marker(ser, marker, seconds)


def interrupt_remote(ser: serial.Serial, attempts: int = 3, timeout: float = 6.0) -> bool:
    """Send terminal INTR, then require a *new* shell echo response.

    Returns False if the remote foreground command could not be confirmed stopped.
    """
    for attempt in range(1, attempts + 1):
        print(f"[UART] Sending remote Ctrl+C ({attempt}/{attempts})...", file=sys.stderr)
        ser.write(b"\x03")
        ser.flush()
        time.sleep(0.2)
        ser.reset_input_buffer()  # Discard previously queued Base64, if any.
        ser.write(b"\r\n")
        ser.flush()
        if probe_shell(ser, seconds=timeout):
            print("[UART] Recovery shell responded; previous transfer stopped.", file=sys.stderr)
            return True
    print(
        "[UART] WARNING: Could not confirm that the remote dd has stopped!\n"
        "[UART] Do not restart dumping until Ctrl+C in a serial terminal"
        " restores the recovery shell prompt.",
        file=sys.stderr,
    )
    return False


def transfer(ser: serial.Serial, args: argparse.Namespace) -> None:
    expected = args.count * SECTOR
    token = secrets.token_hex(8)
    begin = f"__H723_BEGIN_{token}__"
    end = f"__H723_END_{token}__"
    # Kept read-only, matching the published guide.
    command = (
        f"echo {begin}; "
        f"dd if=/dev/block/mmcblk0 bs=512 skip={args.skip} count={args.count} "
        f"2>/dev/null | base64; echo {end}"
    )

    progress = ProgressBar(expected, enabled=not args.no_progress)
    payload_lines: list[str] = []
    payload_chars = 0
    collecting = False
    command_sent = False
    remote_finished = False

    # UART uses 10 serial bits per byte and Base64 expands binary by ~4/3.
    minimum_seconds = expected * (4 / 3) * 10 / args.baud
    print(
        f"[UART] Reading {human_bytes(expected)} from LBA {args.skip} "
        f"({args.count} sectors), baud {args.baud}.\n"
        f"[UART] Theoretical minimum: {human_time(minimum_seconds)}.",
        file=sys.stderr,
    )
    deadline = time.monotonic() + max(30, minimum_seconds * 4 + 20)
    begin_deadline = time.monotonic() + 10.0
    last_payload_time = time.monotonic()

    try:
        send_line(ser, command)
        command_sent = True
        while time.monotonic() < deadline:
            raw = ser.readline()
            if not raw:
                now = time.monotonic()
                if not collecting and now >= begin_deadline:
                    raise TimeoutError("No BEGIN marker from recovery UART shell")
                if collecting and now - last_payload_time >= args.stall_timeout:
                    raise TimeoutError(f"No UART payload received for {args.stall_timeout:g} seconds")
                continue
            line = raw.decode("ascii", errors="ignore").strip()
            if line == begin:
                collecting = True
                payload_lines.clear()
                payload_chars = 0
                last_payload_time = time.monotonic()
                progress.reset_clock()
                progress.update(0, force=True)
                continue
            if line == end:
                remote_finished = True
                if not collecting:
                    raise RuntimeError("END marker arrived before BEGIN marker")
                payload = "".join(payload_lines)
                data = base64.b64decode(payload, validate=True)
                if len(data) != expected:
                    raise RuntimeError(
                        f"Dump length mismatch: got {len(data)}, expected {expected}. "
                        "The remote dd may have failed (its stderr is suppressed)."
                    )
                out = Path(args.out)
                out.write_bytes(data)
                checksum = hashlib.sha256(data).hexdigest()
                progress.finish()  # 100% only after validation AND successful disk write.
                print(f"Saved {out} ({len(data)} bytes)")
                print(f"SHA-256: {checksum}")
                return
            if collecting:
                if not is_base64_line(line):
                    raise RuntimeError(f"Unexpected non-Base64 line inside payload: {line!r}")
                payload_lines.append(line)
                payload_chars += len(line)
                last_payload_time = time.monotonic()
                # Keep the display below 100% until CRC/length checks and file save finish.
                progress.update(min(payload_chars * 3 // 4, int(expected * 0.999)))
        raise TimeoutError("Timed out waiting for UART dump END marker")
    except (KeyboardInterrupt, Exception):
        progress.end_line()
        if command_sent and not remote_finished:
            interrupt_remote(ser)
        raise


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("port", help="UART port, e.g. COM5 or /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--skip", type=int, required=True, help="Starting 512-byte LBA")
    ap.add_argument("--count", type=int, required=True, help="Number of 512-byte sectors")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-progress", action="store_true", help="Disable the progress bar")
    ap.add_argument("--stall-timeout", type=float, default=60.0,
                    help="Abort a stalled UART payload after N seconds (default: 60)")
    ap.add_argument("--no-auto-recover", action="store_true",
                    help="Do not send Ctrl+C automatically when recovery shell is busy")
    args = ap.parse_args()

    if args.skip < 0 or args.count <= 0 or args.baud <= 0 or args.stall_timeout <= 0:
        ap.error("--skip >= 0, --count > 0, --baud > 0 and --stall-timeout > 0 required")

    try:
        with serial.Serial(args.port, args.baud, timeout=0.25, write_timeout=2) as ser:
            try:
                ser.dtr = False
                ser.rts = False
            except (OSError, ValueError):
                pass
            time.sleep(0.3)
            ser.reset_input_buffer()
            ser.write(b"\r\n")
            ser.flush()
            time.sleep(0.2)

            print("[UART] Checking recovery shell...", file=sys.stderr)
            if not probe_shell(ser):
                if args.no_auto_recover:
                    raise RuntimeError("Recovery shell did not respond (auto-recovery disabled)")
                print(
                    "[UART] Shell did not respond; stale dd/base64 may still be running.",
                    file=sys.stderr,
                )
                if not interrupt_remote(ser):
                    raise RuntimeError("Cannot confirm recovery shell is ready; dump not started")
            print("[UART] Recovery shell is ready.", file=sys.stderr)
            transfer(ser, args)
    except KeyboardInterrupt:
        print("[UART] Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)
    except (OSError, ValueError, RuntimeError, TimeoutError, serial.SerialException) as exc:
        print(f"[UART] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()