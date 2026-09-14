#!/usr/bin/env python3
"""Hash-gated Secure Storage writer for the H723 recovery UART shell.

Nothing is written unless --write is supplied. Even then, the script requires
explicit expected SHA-256 values for both the live source image and the
candidate image, saves a pre-write backup, writes changed item blocks first,
backup map next, primary map last, and verifies every write by read-back.
"""

from __future__ import annotations

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
TOTAL = 128 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_sha(value: str) -> str:
    value = value.strip().lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise argparse.ArgumentTypeError("SHA-256 must be exactly 64 hexadecimal characters")
    return value


class UARTShell:
    def __init__(self, port: str, baud: int):
        self.ser = serial.Serial(port, baud, timeout=0.20, write_timeout=3)
        try:
            self.ser.dtr = False
            self.ser.rts = False
        except Exception:
            pass
        time.sleep(0.25)
        self.ser.reset_input_buffer()
        self.send("\r\n")
        time.sleep(0.20)

    def close(self) -> None:
        self.ser.close()

    def send(self, text: str) -> None:
        self.ser.write(text.encode("ascii"))
        self.ser.flush()

    def _readline(self, deadline: float) -> str:
        while time.time() < deadline:
            raw = self.ser.readline()
            if raw:
                return raw.decode("ascii", errors="ignore").replace("\r", "").replace("\n", "")
        raise TimeoutError("UART timeout")

    def command_status(self, command: str, prefix: str, timeout: int = 20) -> int:
        self.ser.reset_input_buffer()
        self.send(command + "\r\n")
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self._readline(deadline).strip()
            if line.startswith(prefix):
                return int(line[len(prefix):])
        raise TimeoutError(f"Timed out waiting for {prefix}")

    def read_emmc(self, lba: int, sectors: int) -> bytes:
        token = secrets.token_hex(8)
        begin = f"__H723_READ_BEGIN_{token}__"
        end = f"__H723_READ_END_{token}__"
        command = (
            f"echo {begin}; dd if=/dev/block/mmcblk0 bs=512 skip={lba} count={sectors} "
            f"2>/dev/null | base64; echo {end}"
        )
        expected = sectors * SECTOR
        estimate = expected * 4 / 3 * 10 / max(self.ser.baudrate, 1)
        deadline = time.time() + max(20, estimate * 4 + 10)
        self.ser.reset_input_buffer()
        self.send(command + "\r\n")
        collecting = False
        lines: list[str] = []
        while time.time() < deadline:
            line = self._readline(deadline).strip()
            if line == begin:
                collecting = True
                lines.clear()
                continue
            if line == end:
                if not collecting:
                    raise RuntimeError("END marker arrived before BEGIN marker")
                data = base64.b64decode("".join(lines), validate=True)
                if len(data) != expected:
                    raise RuntimeError(f"Read length mismatch at LBA {lba}: {len(data)} != {expected}")
                return data
            if collecting:
                if not line or not all(c.isalnum() or c in "+/=" for c in line):
                    raise RuntimeError(f"Unexpected non-Base64 line during read: {line!r}")
                lines.append(line)
        raise TimeoutError(f"Timed out reading LBA {lba}")

    def preflight(self, secure_lba: int) -> None:
        token = secrets.token_hex(6)
        p = f"__H723_B64_{token}__"
        rc = self.command_status(
            f"echo QQ== | base64 -d | dd of=/dev/null bs=1 count=1 2>/dev/null; rc=$?; echo {p}$rc",
            p,
            10,
        )
        if rc != 0:
            raise RuntimeError(f"base64 -d preflight failed: rc={rc}")

        token = secrets.token_hex(6)
        p = f"__H723_OPEN_{token}__"
        rc = self.command_status(
            f"dd if=/dev/null of=/dev/block/mmcblk0 bs=512 seek={secure_lba} count=0 conv=notrunc 2>/dev/null; rc=$?; echo {p}$rc",
            p,
            10,
        )
        if rc != 0:
            raise RuntimeError(f"write-open preflight failed: rc={rc}")

    def write_sector(self, lba: int, sector: bytes) -> None:
        if len(sector) != SECTOR:
            raise ValueError("write_sector requires 512 bytes")
        encoded = base64.b64encode(sector).decode("ascii")
        token = secrets.token_hex(6)
        p = f"__H723_WRITE_{token}__"
        rc = self.command_status(
            f"echo {encoded} | base64 -d | dd of=/dev/block/mmcblk0 bs=512 seek={lba} count=1 conv=notrunc 2>/dev/null; rc=$?; echo {p}$rc",
            p,
            15,
        )
        if rc != 0:
            raise RuntimeError(f"sector write failed at LBA {lba}: rc={rc}")

    def sync(self) -> None:
        token = secrets.token_hex(6)
        p = f"__H723_SYNC_{token}__"
        rc = self.command_status(f"sync; rc=$?; echo {p}$rc", p, 20)
        if rc != 0:
            raise RuntimeError(f"sync failed: rc={rc}")


def changed_blocks(live: bytes, candidate: bytes) -> list[int]:
    if len(live) != TOTAL or len(candidate) != TOTAL:
        raise ValueError("Both images must be exactly 128 KiB")
    return [i for i in range(TOTAL // BLOCK) if live[i * BLOCK:(i + 1) * BLOCK] != candidate[i * BLOCK:(i + 1) * BLOCK]]


def safe_order(blocks: list[int]) -> list[int]:
    order = sorted(b for b in blocks if b not in (0, 1))
    if 1 in blocks:
        order.append(1)
    if 0 in blocks:
        order.append(0)
    return order


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("candidate")
    ap.add_argument("--secure-lba", type=int, required=True, help="Start LBA; 12288 on the tested H723-6621-V1.2 image")
    ap.add_argument("--expected-live-sha256", type=normalize_sha, required=True)
    ap.add_argument("--expected-candidate-sha256", type=normalize_sha, required=True)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--backup-dir", default=".")
    ap.add_argument("--expected-changed-blocks", help="Comma-separated 4 KiB block indexes, e.g. 8,9,10,11,1,0. Required with --write.")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    if args.secure_lba < 0:
        raise SystemExit("--secure-lba must be >= 0")

    candidate = Path(args.candidate).read_bytes()
    if len(candidate) != TOTAL:
        raise SystemExit(f"Candidate size is {len(candidate)}; expected {TOTAL}")
    candidate_sha = sha256(candidate)
    if candidate_sha != args.expected_candidate_sha256:
        raise SystemExit(f"Candidate SHA mismatch: {candidate_sha}")

    shell = UARTShell(args.port, args.baud)
    try:
        live = shell.read_emmc(args.secure_lba, TOTAL // SECTOR)
        live_sha = sha256(live)
        backup_dir = Path(args.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f"h723-secure-storage-before-{datetime.now():%Y%m%d-%H%M%S}.bin"
        backup.write_bytes(live)
        print(f"Live SHA-256:      {live_sha}")
        print(f"Expected live SHA: {args.expected_live_sha256}")
        print(f"Backup:             {backup}")
        if live_sha != args.expected_live_sha256:
            raise SystemExit("REFUSING: live Secure Storage does not match the expected source image")

        blocks = changed_blocks(live, candidate)
        order = safe_order(blocks)
        print(f"Changed 4 KiB blocks: {blocks}")
        print(f"Commit order:         {order}")
        if not blocks:
            print("Live Secure Storage already matches the candidate; nothing to write")
            return
        if not args.write:
            print("READ-ONLY AUDIT PASS. Nothing was written. Add --write only after reviewing the backup and block list.")
            return

        if not args.expected_changed_blocks:
            raise SystemExit("REFUSING: --expected-changed-blocks is required with --write")
        try:
            expected_order = [int(x.strip()) for x in args.expected_changed_blocks.split(",") if x.strip()]
        except ValueError as exc:
            raise SystemExit("Invalid --expected-changed-blocks list") from exc
        if expected_order != order:
            raise SystemExit(
                f"REFUSING: calculated safe commit order {order} does not match "
                f"--expected-changed-blocks {expected_order}"
            )

        shell.preflight(args.secure_lba)
        for block_index in order:
            off = block_index * BLOCK
            block = candidate[off:off + BLOCK]
            lba = args.secure_lba + off // SECTOR
            print(f"Writing block {block_index} -> LBA {lba}..{lba + 7}")
            for i in range(BLOCK // SECTOR):
                shell.write_sector(lba + i, block[i * SECTOR:(i + 1) * SECTOR])
            shell.sync()
            readback = shell.read_emmc(lba, BLOCK // SECTOR)
            if readback != block:
                raise RuntimeError(f"READ-BACK MISMATCH at block {block_index}. DO NOT REBOOT.")
            print("  read-back exact match")

        final = shell.read_emmc(args.secure_lba, TOTAL // SECTOR)
        final_sha = sha256(final)
        print(f"Final SHA-256: {final_sha}")
        if final != candidate or final_sha != args.expected_candidate_sha256:
            Path("h723-secure-storage-final-mismatch.bin").write_bytes(final)
            raise RuntimeError("FINAL VERIFY FAILED. DO NOT REBOOT.")
        Path("h723-secure-storage-after-verified.bin").write_bytes(final)
        print("WRITE + FULL READ-BACK VERIFY PASS. The script did not reboot the board.")
    finally:
        shell.close()


if __name__ == "__main__":
    main()
