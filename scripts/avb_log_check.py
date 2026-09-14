#!/usr/bin/env python3
"""Summarize the last H723 U-Boot cycle in a captured UART log."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def last_group(text: str, pattern: str):
    matches = list(re.finditer(pattern, text, re.I))
    return matches[-1].group(1) if matches else None


def last_cycle(text: str) -> str:
    positions = [m.start() for m in re.finditer(r"(?:HELLO!\s+)?SBOOT is starting!", text, re.I)]
    return text[positions[-1]:] if positions else text


def item_state(text: str, name: str) -> str:
    events = []
    for m in re.finditer(rf"(no item name {re.escape(name)} in the map|name in map {re.escape(name)})", text, re.I):
        events.append(m.group(1).lower())
    if not events:
        return "not observed"
    return "absent" if events[-1].startswith("no item") else "present"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    args = ap.parse_args()
    text = last_cycle(Path(args.log).read_text(encoding="utf-8", errors="ignore"))

    device_state = last_group(text, r"androidboot\.vbmeta\.device_state=([a-z]+)")
    verified = last_group(text, r"androidboot\.verifiedbootstate=([a-z]+)")
    verity = last_group(text, r"androidboot\.veritymode=([a-z]+)")
    digest = last_group(text, r"vbmeta hash is\s+([0-9a-f]{64})")

    print(f"device_unlock item:        {item_state(text, 'device_unlock')}")
    print(f"fastboot_status_flag item: {item_state(text, 'fastboot_status_flag')}")
    print(f"fastboot unlock flag:      {'found' if 'find fastboot unlock flag' in text else 'not observed'}")
    print(f"vbmeta digest:             {digest or 'not observed'}")
    print(f"device_state:              {device_state or 'not observed'}")
    print(f"verifiedbootstate:         {verified or 'not observed'}")
    print(f"veritymode:                {verity or 'not observed'}")
    print(f"orange bootlogo path:      {'observed' if 'orange state:start to display bootlogo' in text else 'not observed'}")

    if device_state == "unlocked" and verified == "orange":
        print("RESULT: UNLOCKED / ORANGE")
    elif device_state == "locked" and verified == "green":
        print("RESULT: LOCKED / GREEN")
    else:
        print("RESULT: state incomplete or different; inspect the full last boot cycle")


if __name__ == "__main__":
    main()
