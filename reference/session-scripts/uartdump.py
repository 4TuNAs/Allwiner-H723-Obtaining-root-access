import argparse
import base64
import re
import secrets
import sys
import time

import serial


def main():
    ap = argparse.ArgumentParser(description="Read-only Allwinner eMMC dumper via recovery UART shell")
    ap.add_argument("port", help="COM port, e.g. COM5")
    ap.add_argument("--baud", type=int, default=115200, help="UART baudrate (default 115200)")
    ap.add_argument("--skip", type=int, required=True, help="Starting eMMC LBA")
    ap.add_argument("--count", type=int, required=True, help="Number of 512-byte sectors")
    ap.add_argument("--out", required=True, help="Output binary file")
    args = ap.parse_args()
    if args.skip < 0:
        raise SystemExit("--skip must be >= 0")
    if args.count <= 0:
        raise SystemExit("--count must be > 0")
    expected = args.count * 512
    token = secrets.token_hex(8)
    begin = f"@@BEGIN_{token}@@"
    end = f"@@END_{token}@@"
    cmd = (
        f"echo '{begin}'; "
        f"dd if=/dev/block/mmcblk0 bs=512 skip={args.skip} count={args.count} 2>/dev/null | base64; "
        f"echo '{end}'"
    )
    print(f"Port:     {args.port}")
    print(f"Baud:     {args.baud}")
    print(f"LBA:      {args.skip}")
    print(f"Sectors:  {args.count}")
    print(f"Expected: {expected} bytes")
    print()
    ser = serial.Serial(args.port, args.baud, timeout=0.25, write_timeout=2)
    try:
        try:
            ser.dtr = False
        except Exception:
            pass
        try:
            ser.rts = False
        except Exception:
            pass
        time.sleep(0.3)
        ser.reset_input_buffer()
        ser.write(b"\r\n")
        ser.flush()
        time.sleep(0.2)
        print("> " + cmd)
        ser.write((cmd + "\r\n").encode("ascii"))
        ser.flush()
        collecting = False
        b64_lines = []
        estimated_seconds = expected * 4 / 3 * 10 / args.baud
        deadline = time.time() + max(30, estimated_seconds * 3 + 20)
        buf = b""
        while time.time() < deadline:
            chunk = ser.read(4096)
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                raw_line, buf = buf.split(b"\n", 1)
                line = raw_line.replace(b"\r", b"").decode("ascii", errors="ignore").strip()
                if line == begin:
                    collecting = True
                    print("BEGIN received")
                    continue
                if line == end:
                    print("END received")
                    collecting = False
                    payload = "".join(b64_lines)
                    payload = re.sub(r"[^A-Za-z0-9+/=]", "", payload)
                    try:
                        data = base64.b64decode(payload, validate=True)
                    except Exception as e:
                        print("Base64 decode failed:", e)
                        with open(args.out + ".bad.b64.txt", "w", encoding="ascii") as f:
                            f.write(payload)
                        raise SystemExit(2)
                    print(f"Decoded {len(data)} / {expected} bytes")
                    if len(data) != expected:
                        with open(args.out + ".bad.bin", "wb") as f:
                            f.write(data)
                        print("ERROR: length mismatch. Not accepting dump as valid.")
                        raise SystemExit(3)
                    with open(args.out, "wb") as f:
                        f.write(data)
                    print(f"Saved: {args.out}")
                    if args.skip == 0 and len(data) >= 1024:
                        print()
                        if data[510:512] == b"\x55\xaa":
                            print("MBR signature: OK (55 AA)")
                        else:
                            print("MBR signature: BAD:", data[510:512].hex())
                        if data[512:520] == b"EFI PART":
                            print("GPT header: OK (EFI PART)")
                        else:
                            print("GPT header: not found at LBA1:", data[512:520])
                    return
                if collecting and line:
                    b64_lines.append(line)
        raise TimeoutError("Timed out waiting for UART dump")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
