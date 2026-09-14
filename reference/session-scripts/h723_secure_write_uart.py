#!/usr/bin/env python3
"""
H723 Secure Storage UART writer with safeguards.

Default mode is READ-ONLY audit.
Actual eMMC writes require the explicit --write flag.

Assumptions for THIS board/dump:
  Secure Storage starts at eMMC LBA 12288
  Size: 128 KiB (256 sectors)
  Sector size: 512 bytes
"""

import argparse
import base64
import hashlib
import secrets
import time
from datetime import datetime
from pathlib import Path

import serial

SECTOR = 512
BLOCK = 4096

SECURE_LBA = 12288
SECURE_SIZE = 128 * 1024
SECURE_SECTORS = SECURE_SIZE // SECTOR

EXPECTED_ORIGINAL_SHA256 = (
    "cc86b0255f07e9cec320285df83899a51354698c70003a8b1b1e56c807820490"
)
EXPECTED_CANDIDATE_SHA256 = (
    "28a017814d6af136ab18f5f76396af4cd37f20cd407abfb613b0e4968c27fcc4"
)

BLOCK_ORDER = [8, 9, 10, 11, 1, 0]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class UARTShell:
    def __init__(self, port: str, baud: int):
        self.ser = serial.Serial(port, baud, timeout=0.20, write_timeout=3)
        try:
            self.ser.dtr = False
        except Exception:
            pass
        try:
            self.ser.rts = False
        except Exception:
            pass
        time.sleep(0.25)
        self.ser.reset_input_buffer()
        self.send_raw("\r\n")
        time.sleep(0.20)

    def close(self):
        self.ser.close()

    def send_raw(self, text: str):
        self.ser.write(text.encode("ascii"))
        self.ser.flush()

    def _readline(self, deadline):
        while time.time() < deadline:
            raw = self.ser.readline()
            if raw:
                return raw.decode("ascii", errors="ignore").replace("\r","").replace("\n","")
        raise TimeoutError("UART timeout")

    def command_until_marker(self, command: str, marker: str, timeout=20):
        self.ser.reset_input_buffer()
        self.send_raw(command + "\r\n")
        deadline = time.time() + timeout
        lines = []
        while time.time() < deadline:
            line = self._readline(deadline).strip()
            if line.startswith(marker):
                return line, lines
            lines.append(line)
        raise TimeoutError(f"Timed out waiting for marker {marker}")

    def read_emmc(self, lba: int, sectors: int) -> bytes:
        token = secrets.token_hex(8)
        begin = f"__H723_READ_BEGIN_{token}__"
        end = f"__H723_READ_END_{token}__"
        cmd = (
            f"echo {begin}; "
            f"dd if=/dev/block/mmcblk0 bs=512 skip={lba} count={sectors} "
            f"2>/dev/null | base64; "
            f"echo {end}"
        )
        expected = sectors * SECTOR
        estimate = expected * 4 / 3 * 10 / max(self.ser.baudrate, 1)
        deadline = time.time() + max(20, estimate * 4 + 10)
        self.ser.reset_input_buffer()
        self.send_raw(cmd + "\r\n")
        collecting = False
        b64_lines = []
        while time.time() < deadline:
            line = self._readline(deadline).strip()
            if line == begin:
                collecting = True
                continue
            if line == end:
                payload = "".join(b64_lines)
                data = base64.b64decode(payload, validate=True)
                if len(data) != expected:
                    raise RuntimeError(f"Read length mismatch at LBA {lba}: {len(data)} != {expected}")
                return data
            if collecting and line:
                if not all(c.isalnum() or c in "+/=" for c in line):
                    raise RuntimeError(f"Unexpected non-base64 UART line while reading LBA {lba}: {line!r}")
                b64_lines.append(line)
        raise TimeoutError(f"Timed out reading LBA {lba}, sectors={sectors}")

    def preflight_write_open(self):
        token = secrets.token_hex(6)
        marker = f"__H723_PREFLIGHT_{token}__"
        cmd = (
            f"dd if=/dev/null of=/dev/block/mmcblk0 bs=512 seek={SECURE_LBA} count=0 conv=notrunc "
            f"2>/dev/null; rc=$?; echo {marker}$rc"
        )
        line, _ = self.command_until_marker(cmd, marker, timeout=10)
        rc_text = line[len(marker):]
        if rc_text != "0":
            raise RuntimeError(f"Write-open preflight failed (rc={rc_text!r}). No eMMC data was written.")

    def preflight_base64_decode(self):
        token = secrets.token_hex(6)
        marker = f"__H723_B64_{token}__"
        cmd = (
            f"echo QQ== | base64 -d | dd of=/dev/null bs=1 count=1 2>/dev/null; "
            f"rc=$?; echo {marker}$rc"
        )
        line, _ = self.command_until_marker(cmd, marker, timeout=10)
        rc_text = line[len(marker):]
        if rc_text != "0":
            raise RuntimeError(f"base64 -d preflight failed (rc={rc_text!r}). No eMMC data was written.")

    def write_sector(self, lba: int, sector_data: bytes):
        if len(sector_data) != SECTOR:
            raise ValueError("write_sector requires exactly 512 bytes")
        encoded = base64.b64encode(sector_data).decode("ascii")
        token = secrets.token_hex(6)
        marker = f"__H723_WRITE_{token}__"
        cmd = (
            f"echo {encoded} | base64 -d | dd of=/dev/block/mmcblk0 bs=512 seek={lba} "
            f"count=1 conv=notrunc 2>/dev/null; rc=$?; echo {marker}$rc"
        )
        line, _ = self.command_until_marker(cmd, marker, timeout=15)
        rc_text = line[len(marker):]
        if rc_text != "0":
            raise RuntimeError(f"Sector write failed at LBA {lba} (rc={rc_text!r})")

    def sync(self):
        token = secrets.token_hex(6)
        marker = f"__H723_SYNC_{token}__"
        cmd = f"sync; rc=$?; echo {marker}$rc"
        line, _ = self.command_until_marker(cmd, marker, timeout=20)
        rc_text = line[len(marker):]
        if rc_text != "0":
            raise RuntimeError(f"sync failed (rc={rc_text!r})")


def local_candidate_checks(candidate: bytes):
    if len(candidate) != SECURE_SIZE:
        raise SystemExit(f"Candidate size is {len(candidate)} bytes; expected {SECURE_SIZE}")
    h = sha256(candidate)
    print(f"Candidate SHA-256: {h}")
    if h != EXPECTED_CANDIDATE_SHA256:
        raise SystemExit("REFUSING: candidate SHA-256 does not match the validated H723 image.")


def audit_live(shell: UARTShell, backup_dir: Path):
    print(f"Reading live Secure Storage: LBA {SECURE_LBA}..{SECURE_LBA + SECURE_SECTORS - 1}")
    live = shell.read_emmc(SECURE_LBA, SECURE_SECTORS)
    h = sha256(live)
    print(f"Live SHA-256:      {h}")
    print(f"Expected original: {EXPECTED_ORIGINAL_SHA256}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = backup_dir / f"h723-secure-storage-before-{stamp}.bin"
    backup.write_bytes(live)
    print(f"Local backup saved: {backup}")
    if h != EXPECTED_ORIGINAL_SHA256:
        raise SystemExit("\nREFUSING TO WRITE: live Secure Storage differs from the known original dump. Nothing has been written.")
    print("Live image matches the known original dump exactly.")
    return live, backup


def write_block(shell: UARTShell, candidate: bytes, block_index: int):
    off = block_index * BLOCK
    block = candidate[off:off + BLOCK]
    start_lba = SECURE_LBA + off // SECTOR
    print(f"\nWriting 4 KiB block {block_index} (offset 0x{off:05x}, LBA {start_lba}-{start_lba + 7})")
    for i in range(8):
        sector = block[i * SECTOR:(i + 1) * SECTOR]
        shell.write_sector(start_lba + i, sector)
        print(f"  sector {i + 1}/8 OK", end="\r", flush=True)
    print("  8/8 sectors sent     ")
    shell.sync()
    readback = shell.read_emmc(start_lba, 8)
    got = sha256(readback)
    print(f"  read-back SHA-256: {got}")
    if readback != block:
        raise RuntimeError(f"READ-BACK MISMATCH for block {block_index}. STOPPING immediately. Do NOT reboot the board.")
    print("  read-back: EXACT MATCH")


def main():
    ap = argparse.ArgumentParser(description="Safeguarded H723 Secure Storage writer over recovery UART")
    ap.add_argument("port", help="UART port, e.g. COM5")
    ap.add_argument("candidate", help="Validated 128 KiB H723 Secure Storage candidate image")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--backup-dir", default=".", help="Directory for automatic pre-write backup")
    ap.add_argument("--write", action="store_true", help="ACTUALLY WRITE eMMC. Without this flag the script is read-only.")
    args = ap.parse_args()
    candidate = Path(args.candidate).read_bytes()
    local_candidate_checks(candidate)
    shell = UARTShell(args.port, args.baud)
    try:
        live, backup = audit_live(shell, Path(args.backup_dir))
        print("\nChanged 4 KiB blocks planned:")
        for b in BLOCK_ORDER:
            off = b * BLOCK
            lba = SECURE_LBA + off // SECTOR
            print(f"  block {b:2d}: offset 0x{off:05x}, LBA {lba}-{lba + 7}")
        if not args.write:
            print("\nREAD-ONLY AUDIT COMPLETE.\nNothing was written to eMMC.\nRun again with --write only when you intend to commit the patch.")
            return
        print("\nWRITE MODE ENABLED.")
        print("Preflight: testing base64 decoder...")
        shell.preflight_base64_decode()
        print("  OK")
        print("Preflight: testing write-open with count=0...")
        shell.preflight_write_open()
        print("  OK (zero bytes transferred)")
        print("\nCommit order deliberately writes new item copies first, backup map next, primary map LAST.")
        for block_index in BLOCK_ORDER:
            write_block(shell, candidate, block_index)
        print("\nFinal full 128 KiB read-back...")
        final = shell.read_emmc(SECURE_LBA, SECURE_SECTORS)
        final_hash = sha256(final)
        print(f"Final SHA-256:     {final_hash}")
        print(f"Candidate SHA-256: {EXPECTED_CANDIDATE_SHA256}")
        if final != candidate:
            bad = Path("h723-secure-storage-final-mismatch.bin")
            bad.write_bytes(final)
            raise RuntimeError(f"FINAL VERIFY FAILED. Read-back saved to {bad}. DO NOT REBOOT THE BOARD.")
        verified = Path("h723-secure-storage-after-verified.bin")
        verified.write_bytes(final)
        print("\n==============================================")
        print("WRITE + READ-BACK VERIFIED SUCCESSFULLY")
        print("==============================================")
        print(f"Verified image saved locally: {verified}")
        print(f"Original backup:              {backup}")
        print()
        print("The script has NOT rebooted the board.")
        print("Keep UART attached and reboot manually only after reviewing this result.")
    finally:
        shell.close()


if __name__ == "__main__":
    main()
