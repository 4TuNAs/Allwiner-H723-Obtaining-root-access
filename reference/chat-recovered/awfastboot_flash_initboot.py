#!/usr/bin/env python3
import argparse, hashlib, sys
import usb.core, usb.util

VID=0x1F3A
PID=0x1010
PART="init_boot_a"
EXPECTED_SIZE=8388608
EXPECTED_SHA="c1e41476e9cb34b4f7d1599b31f1f882d7b8257b03623020f5c02529e402bf91"

def recv(dev, ep_in, timeout=10000):
    while True:
        raw = bytes(dev.read(ep_in, 4096, timeout=timeout))
        s = raw.decode("ascii", errors="replace")
        print("<", repr(s))
        if s.startswith("INFO"):
            continue
        return s

def cmd(dev, ep_out, ep_in, text, timeout=10000):
    print(">", text)
    dev.write(ep_out, text.encode("ascii"), timeout=timeout)
    return recv(dev, ep_in, timeout)

ap=argparse.ArgumentParser()
ap.add_argument("image")
ap.add_argument("--yes", action="store_true")
a=ap.parse_args()

data=open(a.image,"rb").read()
sha=hashlib.sha256(data).hexdigest()
print("Size:", len(data))
print("SHA256:", sha)

if len(data)!=EXPECTED_SIZE:
    raise SystemExit("REFUSE: wrong image size")
if sha.lower()!=EXPECTED_SHA:
    raise SystemExit("REFUSE: SHA256 differs from expected patched image")

dev=usb.core.find(idVendor=VID,idProduct=PID)
if dev is None:
    raise SystemExit("1f3a:1010 not found")

try:
    dev.set_configuration()
except usb.core.USBError:
    pass

cfg=dev.get_active_configuration()
intf=None
ep_out=ep_in=None
for i in cfg:
    if (i.bInterfaceClass,i.bInterfaceSubClass,i.bInterfaceProtocol)==(0xff,0x42,0x03):
        intf=i
        for ep in i:
            if usb.util.endpoint_direction(ep.bEndpointAddress)==usb.util.ENDPOINT_OUT:
                ep_out=ep.bEndpointAddress
            else:
                ep_in=ep.bEndpointAddress
        break

if intf is None or ep_out is None or ep_in is None:
    raise SystemExit("fastboot interface not found")

try:
    if dev.is_kernel_driver_active(intf.bInterfaceNumber):
        dev.detach_kernel_driver(intf.bInterfaceNumber)
except Exception:
    pass

usb.util.claim_interface(dev,intf.bInterfaceNumber)

try:
    r=cmd(dev,ep_out,ep_in,"getvar:max-download-size")
    if not r.startswith("OKAY"):
        raise SystemExit("getvar failed")
    if not a.yes:
        print("DRY RUN. Nothing flashed.")
        print("Run again with --yes to flash init_boot_a.")
        raise SystemExit(0)
    size_hex=f"{len(data):08x}"
    print(">", "download:"+size_hex)
    dev.write(ep_out,("download:"+size_hex).encode("ascii"),timeout=10000)
    r=recv(dev,ep_in,10000)
    if not r.startswith("DATA"):
        raise SystemExit("download not accepted")
    print("Sending image...")
    off=0
    chunk=1024*1024
    while off<len(data):
        part=data[off:off+chunk]
        dev.write(ep_out,part,timeout=30000)
        off+=len(part)
        print(f"\r{off}/{len(data)}",end="",flush=True)
    print()
    r=recv(dev,ep_in,30000)
    if not r.startswith("OKAY"):
        raise SystemExit("download stage failed")
    r=cmd(dev,ep_out,ep_in,"flash:"+PART,timeout=120000)
    if not r.startswith("OKAY"):
        raise SystemExit("FLASH FAILED")
    print("FLASH OK. No reboot command sent.")
finally:
    try:
        usb.util.release_interface(dev,intf.bInterfaceNumber)
    except Exception:
        pass
    usb.util.dispose_resources(dev)
