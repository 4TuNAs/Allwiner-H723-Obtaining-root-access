#!/usr/bin/env python3
"""Validate and inspect a primary GPT dump captured from the H723 eMMC.

The input is normally the first 34 sectors produced by uart_dump.py.
This version validates both the GPT header CRC and partition-entry-array CRC
before printing partition LBAs or generating dump commands.
"""

from __future__ import annotations

import argparse
import json
import struct
import uuid
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path

SECTOR = 512
GPT_MAGIC = b"EFI PART"


@dataclass
class Partition:
    number: int
    name: str
    first_lba: int
    last_lba: int
    sectors: int
    bytes: int
    type_guid: str
    unique_guid: str


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def parse_gpt(data: bytes) -> tuple[dict, list[Partition]]:
    if len(data) < 2 * SECTOR:
        raise ValueError("Input is too short to contain MBR + GPT header")
    if data[510:512] != b"\x55\xaa":
        raise ValueError("Invalid MBR signature; expected 55 aa at bytes 510..511")

    hdr_sector = data[SECTOR:2 * SECTOR]
    if hdr_sector[:8] != GPT_MAGIC:
        raise ValueError("GPT signature EFI PART not found at LBA 1")

    revision, header_size, stored_header_crc = struct.unpack_from("<III", hdr_sector, 8)
    if not 92 <= header_size <= SECTOR:
        raise ValueError(f"Unsupported GPT header size: {header_size}")

    header_for_crc = bytearray(hdr_sector[:header_size])
    struct.pack_into("<I", header_for_crc, 16, 0)
    calculated_header_crc = crc32(header_for_crc)
    if calculated_header_crc != stored_header_crc:
        raise ValueError(
            f"GPT header CRC mismatch: stored={stored_header_crc:08x} "
            f"calculated={calculated_header_crc:08x}"
        )

    current_lba = struct.unpack_from("<Q", hdr_sector, 24)[0]
    backup_lba = struct.unpack_from("<Q", hdr_sector, 32)[0]
    first_usable = struct.unpack_from("<Q", hdr_sector, 40)[0]
    last_usable = struct.unpack_from("<Q", hdr_sector, 48)[0]
    disk_guid = str(uuid.UUID(bytes_le=hdr_sector[56:72]))
    entries_lba = struct.unpack_from("<Q", hdr_sector, 72)[0]
    entry_count = struct.unpack_from("<I", hdr_sector, 80)[0]
    entry_size = struct.unpack_from("<I", hdr_sector, 84)[0]
    stored_entries_crc = struct.unpack_from("<I", hdr_sector, 88)[0]

    if entry_size < 128 or entry_size % 8:
        raise ValueError(f"Suspicious GPT entry size: {entry_size}")

    entries_offset = entries_lba * SECTOR
    entries_length = entry_count * entry_size
    end = entries_offset + entries_length
    if end > len(data):
        raise ValueError(
            f"Input does not contain the complete primary partition array: "
            f"need {end} bytes, have {len(data)}"
        )

    entries_raw = data[entries_offset:end]
    calculated_entries_crc = crc32(entries_raw)
    if calculated_entries_crc != stored_entries_crc:
        raise ValueError(
            f"GPT entry-array CRC mismatch: stored={stored_entries_crc:08x} "
            f"calculated={calculated_entries_crc:08x}"
        )

    partitions: list[Partition] = []
    for idx in range(entry_count):
        ent = entries_raw[idx * entry_size:(idx + 1) * entry_size]
        if ent[:16] == b"\0" * 16:
            continue
        first_lba, last_lba = struct.unpack_from("<QQ", ent, 32)
        if last_lba < first_lba:
            raise ValueError(f"Partition entry {idx + 1} has last_lba < first_lba")
        name = ent[56:entry_size].decode("utf-16-le", errors="replace").split("\0", 1)[0]
        sectors = last_lba - first_lba + 1
        partitions.append(
            Partition(
                number=idx + 1,
                name=name,
                first_lba=first_lba,
                last_lba=last_lba,
                sectors=sectors,
                bytes=sectors * SECTOR,
                type_guid=str(uuid.UUID(bytes_le=ent[:16])),
                unique_guid=str(uuid.UUID(bytes_le=ent[16:32])),
            )
        )

    meta = {
        "revision": f"0x{revision:08x}",
        "header_size": header_size,
        "header_crc32": f"{stored_header_crc:08x}",
        "current_lba": current_lba,
        "backup_lba": backup_lba,
        "first_usable_lba": first_usable,
        "last_usable_lba": last_usable,
        "disk_guid": disk_guid,
        "entries_lba": entries_lba,
        "entry_count": entry_count,
        "entry_size": entry_size,
        "entries_crc32": f"{stored_entries_crc:08x}",
    }
    return meta, partitions


def mib(n: int) -> str:
    return f"{n / 1024 / 1024:.2f} MiB"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("gpt", help="Primary GPT dump, normally gpt34.bin")
    ap.add_argument("--json", action="store_true", help="Print JSON")
    ap.add_argument("--show-guids", action="store_true", help="Print device/partition GUIDs")
    ap.add_argument("--dump-plan", metavar="PORT", help="Print uart_dump.py commands for important _a partitions")
    args = ap.parse_args()

    meta, parts = parse_gpt(Path(args.gpt).read_bytes())

    if args.json:
        safe_meta = dict(meta)
        if not args.show_guids:
            safe_meta.pop("disk_guid", None)
        rows = []
        for p in parts:
            d = asdict(p)
            if not args.show_guids:
                d.pop("type_guid", None)
                d.pop("unique_guid", None)
            rows.append(d)
        print(json.dumps({"gpt": safe_meta, "partitions": rows}, indent=2))
        return

    print("GPT validation: PASS")
    print(f"Header CRC32: {meta['header_crc32']}")
    print(f"Entry-array CRC32: {meta['entries_crc32']}")
    print(f"Entries: {meta['entry_count']} x {meta['entry_size']} bytes")
    if args.show_guids:
        print(f"Disk GUID: {meta['disk_guid']}")
    print()
    print(f"{'#':>2} {'name':22} {'first LBA':>11} {'last LBA':>11} {'sectors':>10} {'size':>10}")
    for p in parts:
        print(f"{p.number:2d} {p.name:22} {p.first_lba:11d} {p.last_lba:11d} {p.sectors:10d} {mib(p.bytes):>10}")

    if args.dump_plan:
        wanted = {"boot_a", "vendor_boot_a", "init_boot_a", "misc", "vbmeta_a", "dtbo_a", "env_a"}
        print("\n# Suggested read-only backups; verify names/LBAs above first")
        for p in parts:
            if p.name in wanted:
                print(
                    f'python scripts/uart_dump.py {args.dump_plan} --skip {p.first_lba} '
                    f'--count {p.sectors} --out {p.name}-stock.img'
                )


if __name__ == "__main__":
    main()
