#!/usr/bin/env python3
"""Capture raw UART output to a file while mirroring it to the console."""

import argparse
import sys
import serial

ap = argparse.ArgumentParser()
ap.add_argument("port")
ap.add_argument("--baud", type=int, default=115200)
ap.add_argument("--out", required=True)
args = ap.parse_args()

ser = serial.Serial(args.port, args.baud, timeout=0.2)
try:
    try:
        ser.dtr = False
        ser.rts = False
    except Exception:
        pass
    print(f"Capturing {args.port} @ {args.baud} to {args.out}; Ctrl+C stops")
    with open(args.out, "wb") as f:
        while True:
            data = ser.read(4096)
            if data:
                f.write(data)
                f.flush()
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
except KeyboardInterrupt:
    print("\nStopped")
finally:
    ser.close()
