import sys
import time
import base64
import secrets
import struct
import uuid

import serial


if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} COM5")
    sys.exit(1)

PORT = sys.argv[1]
BAUD = 115200

LBA = 0
COUNT = 34
EXPECTED = COUNT * 512
OUTFILE = "gpt34.bin"

token = secrets.token_hex(6)
BEGIN = f"__H723_BEGIN_{token}__"
END   = f"__H723_END_{token}__"


def parse_gpt(data):
    print("\n=== GPT ANALYSIS ===")
    if len(data) < 1024:
        print("Too short")
        return
    print("MBR signature:", data[510:512].hex(" "))
    hdr = data[512:1024]
    if hdr[:8] != b"EFI PART":
        print("GPT signature NOT found at LBA1")
        print("LBA1 first 32 bytes:", hdr[:32].hex(" "))
        return
    print("GPT signature: EFI PART")
    revision = struct.unpack_from("<I", hdr, 8)[0]
    header_size = struct.unpack_from("<I", hdr, 12)[0]
    current_lba = struct.unpack_from("<Q", hdr, 24)[0]
    backup_lba = struct.unpack_from("<Q", hdr, 32)[0]
    first_usable = struct.unpack_from("<Q", hdr, 40)[0]
    last_usable = struct.unpack_from("<Q", hdr, 48)[0]
    disk_guid = uuid.UUID(bytes_le=hdr[56:72])
    entries_lba = struct.unpack_from("<Q", hdr, 72)[0]
    num_entries = struct.unpack_from("<I", hdr, 80)[0]
    entry_size = struct.unpack_from("<I", hdr, 84)[0]
    print(f"Revision:       0x{revision:08x}")
    print(f"Header size:    {header_size}")
    print(f"Current LBA:    {current_lba}")
    print(f"Backup LBA:     {backup_lba}")
    print(f"First usable:   {first_usable}")
    print(f"Last usable:    {last_usable}")
    print(f"Disk GUID:      {disk_guid}")
    print(f"Entries LBA:    {entries_lba}")
    print(f"Entry count:    {num_entries}")
    print(f"Entry size:     {entry_size}")
    offset = entries_lba * 512
    print("\n=== PARTITIONS ===")
    for i in range(num_entries):
        pos = offset + i * entry_size
        if pos + entry_size > len(data):
            break
        ent = data[pos:pos + entry_size]
        type_guid_raw = ent[0:16]
        if type_guid_raw == b"\x00" * 16:
            continue
        type_guid = uuid.UUID(bytes_le=type_guid_raw)
        unique_guid = uuid.UUID(bytes_le=ent[16:32])
        first = struct.unpack_from("<Q", ent, 32)[0]
        last = struct.unpack_from("<Q", ent, 40)[0]
        attrs = struct.unpack_from("<Q", ent, 48)[0]
        name_raw = ent[56:entry_size]
        try:
            name = name_raw.decode("utf-16-le", errors="ignore").split("\x00", 1)[0]
        except Exception:
            name = "?"
        sectors = last - first + 1
        size = sectors * 512
        print(f"{i + 1:2d} {name:20s} LBA {first:10d} - {last:10d} {size / 1024 / 1024:8.2f} MiB")


ser = serial.Serial(PORT, BAUD, timeout=0.25, write_timeout=2)
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
    command = (
        f"echo {BEGIN}; "
        f"dd if=/dev/block/mmcblk0 bs=512 skip={LBA} count={COUNT} 2>/dev/null | base64; "
        f"echo {END}"
    )
    print("Sending:")
    print(command)
    print()
    ser.write((command + "\r\n").encode("ascii"))
    ser.flush()
    collecting = False
    lines = []
    estimated = EXPECTED * 4 / 3 * 10 / BAUD
    deadline = time.time() + max(30, estimated * 4 + 10)
    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode("ascii", errors="ignore").replace("\r", "").replace("\n", "").strip()
        if line == BEGIN:
            print("BEGIN")
            collecting = True
            continue
        if line == END:
            print("END")
            break
        if collecting:
            if line and all(c.isalnum() or c in "+/=" for c in line):
                lines.append(line)
    else:
        raise RuntimeError("Timeout waiting for END marker")
    payload = "".join(lines)
    data = base64.b64decode(payload, validate=True)
    print(f"\nReceived: {len(data)} bytes")
    print(f"Expected: {EXPECTED} bytes")
    if len(data) != EXPECTED:
        with open("gpt34_bad.bin", "wb") as f:
            f.write(data)
        raise RuntimeError("Dump length mismatch - not accepting it")
    with open(OUTFILE, "wb") as f:
        f.write(data)
    print(f"Saved: {OUTFILE}")
    parse_gpt(data)
finally:
    ser.close()
