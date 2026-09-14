#!/usr/bin/env python3
"""Inspect and patch the Allwinner Secure Storage layout observed on H723-6621-V1.2.

This hardened version verifies the exact unlock payloads, duplicate names,
primary/backup copies and CRCs. It refuses to overwrite an existing unlock
item whose value is not the expected one.
"""

from __future__ import annotations

import argparse
import struct
import zlib
from collections import Counter
from pathlib import Path

MAGIC = 0x17253948
BLOCK = 4096
TOTAL = 131072
MAP_MAGIC_OFF = 4088
MAP_CRC_OFF = 4092
ITEM_CRC_OFF = 3172
MAX_PAYLOAD = 3072
UNLOCK_ITEMS = {
    "fastboot_status_flag": b"unlocked",
    "device_unlock": b"unlock",
}


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def parse_map(block: bytes) -> tuple[list[tuple[str, int]], int, int, int]:
    if len(block) != BLOCK:
        raise ValueError("Map block must be exactly 4096 bytes")
    entries: list[tuple[str, int]] = []
    pos = 0
    while pos < MAP_MAGIC_OFF:
        end = block.find(b"\0", pos, MAP_MAGIC_OFF)
        if end < 0:
            raise ValueError("Unterminated map entry")
        if end == pos:
            break
        raw = block[pos:end]
        try:
            text = raw.decode("ascii")
            name, size_text = text.rsplit(":", 1)
            size = int(size_text)
        except Exception as exc:
            raise ValueError(f"Invalid map entry at offset {pos}: {raw!r}") from exc
        if not name:
            raise ValueError("Empty Secure Storage item name")
        entries.append((name, size))
        pos = end + 1
    magic = struct.unpack_from("<I", block, MAP_MAGIC_OFF)[0]
    stored_crc = struct.unpack_from("<I", block, MAP_CRC_OFF)[0]
    return entries, magic, stored_crc, crc32(block[:MAP_CRC_OFF])


def parse_item(block: bytes) -> dict:
    if len(block) != BLOCK:
        raise ValueError("Item block must be exactly 4096 bytes")
    actual_len = struct.unpack_from("<I", block, 96)[0]
    if actual_len > MAX_PAYLOAD:
        raise ValueError(f"Item payload length {actual_len} exceeds {MAX_PAYLOAD}")
    return {
        "magic": struct.unpack_from("<I", block, 0)[0],
        "item_id": struct.unpack_from("<i", block, 4)[0],
        "name": block[8:72].split(b"\0", 1)[0].decode("ascii", errors="strict"),
        "re_encrypt": struct.unpack_from("<I", block, 72)[0],
        "version": struct.unpack_from("<I", block, 76)[0],
        "actual_len": actual_len,
        "payload": block[100:100 + actual_len],
        "stored_crc": struct.unpack_from("<I", block, ITEM_CRC_OFF)[0],
        "calculated_crc": crc32(block[:ITEM_CRC_OFF]),
    }


def inspect(data: bytes, require_unlock: bool = False) -> tuple[list[tuple[str, int]], dict[str, dict]]:
    if len(data) != TOTAL:
        raise ValueError(f"Wrong Secure Storage size: {len(data)}; expected {TOTAL}")

    primary_map = data[:BLOCK]
    backup_map = data[BLOCK:2 * BLOCK]
    entries, magic, stored_crc, calc_crc = parse_map(primary_map)

    errors: list[str] = []
    if magic != MAGIC:
        errors.append(f"map magic is 0x{magic:08x}, expected 0x{MAGIC:08x}")
    if stored_crc != calc_crc:
        errors.append("primary map CRC mismatch")
    if primary_map != backup_map:
        errors.append("primary and backup maps differ")

    counts = Counter(name for name, _ in entries)
    duplicates = [name for name, count in counts.items() if count != 1]
    if duplicates:
        errors.append(f"duplicate item names: {duplicates}")

    required_bytes = 2 * BLOCK + len(entries) * 2 * BLOCK
    if required_bytes > TOTAL:
        errors.append("map points beyond the 128 KiB Secure Storage region")

    items: dict[str, dict] = {}
    for index, (name, size_token) in enumerate(entries):
        off = 2 * BLOCK + index * 2 * BLOCK
        primary = data[off:off + BLOCK]
        backup = data[off + BLOCK:off + 2 * BLOCK]
        if len(primary) != BLOCK or len(backup) != BLOCK:
            errors.append(f"item {name} is outside the image")
            continue
        try:
            item = parse_item(primary)
        except Exception as exc:
            errors.append(f"item {name}: {exc}")
            continue
        if item["magic"] != MAGIC:
            errors.append(f"item {name}: bad magic")
        if item["name"] != name:
            errors.append(f"item map/name mismatch: map={name!r}, item={item['name']!r}")
        if item["stored_crc"] != item["calculated_crc"]:
            errors.append(f"item {name}: CRC mismatch")
        if primary != backup:
            errors.append(f"item {name}: primary/backup differ")
        item["index"] = index
        item["size_token"] = size_token
        items[name] = item

    if require_unlock:
        for name, expected_payload in UNLOCK_ITEMS.items():
            item = items.get(name)
            if item is None:
                errors.append(f"required unlock item {name!r} is missing")
                continue
            if item["re_encrypt"] != 0:
                errors.append(f"unlock item {name!r} is not plaintext")
            if item["payload"] != expected_payload:
                errors.append(
                    f"unlock item {name!r} has payload {item['payload']!r}; "
                    f"expected {expected_payload!r}"
                )

    if errors:
        raise ValueError("Secure Storage verification failed:\n - " + "\n - ".join(errors))
    return entries, items


def build_item(name: str, payload: bytes) -> bytes:
    if not name or len(name.encode("ascii")) >= 64:
        raise ValueError("Item name is empty or too long")
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("Payload is too large")
    block = bytearray(BLOCK)
    struct.pack_into("<II", block, 0, MAGIC, 0)
    encoded_name = name.encode("ascii")
    block[8:8 + len(encoded_name)] = encoded_name
    struct.pack_into("<I", block, 72, 0)
    struct.pack_into("<I", block, 76, 1)
    struct.pack_into("<I", block, 96, len(payload))
    block[100:100 + len(payload)] = payload
    struct.pack_into("<I", block, ITEM_CRC_OFF, crc32(block[:ITEM_CRC_OFF]))
    return bytes(block)


def build_map(entries: list[tuple[str, int]]) -> bytes:
    block = bytearray(BLOCK)
    pos = 0
    for name, size_token in entries:
        raw = f"{name}:{size_token}".encode("ascii") + b"\0"
        if pos + len(raw) > MAP_MAGIC_OFF:
            raise ValueError("Secure Storage map is full")
        block[pos:pos + len(raw)] = raw
        pos += len(raw)
    struct.pack_into("<I", block, MAP_MAGIC_OFF, MAGIC)
    struct.pack_into("<I", block, MAP_CRC_OFF, crc32(block[:MAP_CRC_OFF]))
    return bytes(block)


def patch(data: bytes) -> bytes:
    entries, items = inspect(data, require_unlock=False)
    size_tokens = {size for _, size in entries}
    if len(size_tokens) != 1:
        raise ValueError(f"Mixed map size tokens are unsupported: {sorted(size_tokens)}")
    size_token = next(iter(size_tokens), 3176)
    if entries and size_token != 3176:
        raise ValueError(f"Unexpected map size token {size_token}; refusing to guess")

    output = bytearray(data)
    names = {name for name, _ in entries}
    for name, expected_payload in UNLOCK_ITEMS.items():
        if name in names:
            item = items[name]
            if item["payload"] != expected_payload or item["re_encrypt"] != 0:
                raise ValueError(
                    f"Existing {name!r} does not already contain the expected plaintext value; refusing to overwrite it"
                )
            print(f"{name}: already present with the expected value")
            continue

        index = len(entries)
        off = 2 * BLOCK + index * 2 * BLOCK
        if off + 2 * BLOCK > TOTAL:
            raise ValueError("No room for another Secure Storage item")
        item_block = build_item(name, expected_payload)
        output[off:off + BLOCK] = item_block
        output[off + BLOCK:off + 2 * BLOCK] = item_block
        entries.append((name, size_token))
        names.add(name)
        print(f"Added {name} at item index {index}, offsets 0x{off:x}/0x{off + BLOCK:x}")

    map_block = build_map(entries)
    output[:BLOCK] = map_block
    output[BLOCK:2 * BLOCK] = map_block
    inspect(bytes(output), require_unlock=True)
    return bytes(output)


def print_summary(entries: list[tuple[str, int]], items: dict[str, dict]) -> None:
    print("VERIFY PASS")
    for name, size_token in entries:
        item = items[name]
        preview = ""
        if item["re_encrypt"] == 0 and item["actual_len"] <= 64:
            try:
                preview = f" value={item['payload'].decode('ascii')!r}"
            except UnicodeDecodeError:
                pass
        print(
            f"[{item['index']:02d}] {name:24} size_token={size_token} "
            f"len={item['actual_len']:4d}{preview}"
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    verify_p = sub.add_parser("verify")
    verify_p.add_argument("image")
    verify_p.add_argument("--require-unlock", action="store_true")
    patch_p = sub.add_parser("patch")
    patch_p.add_argument("input")
    patch_p.add_argument("output")
    args = ap.parse_args()

    if args.command == "verify":
        entries, items = inspect(Path(args.image).read_bytes(), args.require_unlock)
        print_summary(entries, items)
    else:
        src = Path(args.input).read_bytes()
        out = patch(src)
        Path(args.output).write_bytes(out)
        print(f"Wrote {args.output}")
        entries, items = inspect(out, require_unlock=True)
        print_summary(entries, items)


if __name__ == "__main__":
    main()
