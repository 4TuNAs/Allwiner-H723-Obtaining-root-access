#!/usr/bin/env python3
import argparse, struct, zlib
from pathlib import Path

MAGIC = 0x17253948
BLOCK = 4096
TOTAL = 131072
MAP_MAGIC_OFF = 4088
MAP_CRC_OFF = 4092
ITEM_CRC_OFF = 3172

def crc32(b): return zlib.crc32(b) & 0xffffffff

def parse_map(m):
    entries=[]; pos=0
    while pos < MAP_MAGIC_OFF:
        end=m.find(b"\0", pos, MAP_MAGIC_OFF)
        if end < 0 or end == pos: break
        s=m[pos:end].decode("ascii")
        name,size=s.rsplit(":",1)
        entries.append((name,int(size)))
        pos=end+1
    magic=struct.unpack_from("<I",m,MAP_MAGIC_OFF)[0]
    stored=struct.unpack_from("<I",m,MAP_CRC_OFF)[0]
    calc=crc32(m[:MAP_CRC_OFF])
    return entries,magic,stored,calc

def parse_item(b):
    ln=struct.unpack_from("<I",b,96)[0]
    return dict(
        magic=struct.unpack_from("<I",b,0)[0],
        item_id=struct.unpack_from("<i",b,4)[0],
        name=b[8:72].split(b"\0",1)[0].decode("ascii",errors="replace"),
        re_encrypt=struct.unpack_from("<I",b,72)[0],
        version=struct.unpack_from("<I",b,76)[0],
        actual_len=ln,
        payload=b[100:100+min(ln,3072)],
        stored_crc=struct.unpack_from("<I",b,ITEM_CRC_OFF)[0],
        calc_crc=crc32(b[:ITEM_CRC_OFF]),
    )

def verify(data, require_unlock=False):
    if len(data)!=TOTAL:
        raise SystemExit(f"Wrong size: {len(data)}, expected {TOTAL}")
    entries,magic,stored,calc=parse_map(data[:BLOCK])
    errors=0
    print(f"Map magic: 0x{magic:08x}")
    print(f"Map CRC: {'OK' if stored==calc else 'FAIL'}")
    print(f"Map backup: {'OK' if data[:BLOCK]==data[BLOCK:2*BLOCK] else 'FAIL'}")
    if magic!=MAGIC or stored!=calc or data[:BLOCK]!=data[BLOCK:2*BLOCK]:
        errors += 1
    for i,(name,size_token) in enumerate(entries):
        off=2*BLOCK+i*2*BLOCK
        p=data[off:off+BLOCK]; q=data[off+BLOCK:off+2*BLOCK]
        it=parse_item(p)
        crc_ok=it["stored_crc"]==it["calc_crc"]
        bak_ok=p==q
        pv=""
        if it["re_encrypt"]==0 and it["actual_len"]<=64:
            try: pv=" = "+repr(it["payload"].decode("ascii"))
            except: pass
        print(f"[{i}] {name:22s} map_size={size_token} len={it['actual_len']:4d} "
              f"CRC={'OK' if crc_ok else 'FAIL'} backup={'OK' if bak_ok else 'FAIL'}{pv}")
        if it["magic"]!=MAGIC or it["name"]!=name or not crc_ok or not bak_ok:
            errors += 1
    names={n for n,_ in entries}
    if require_unlock:
        for n in ("fastboot_status_flag","device_unlock"):
            if n not in names:
                print("Missing:",n); errors+=1
    if errors:
        raise SystemExit(f"VERIFY FAILED: {errors} error(s)")
    print("VERIFY PASS")
    return entries

def build_item(name,payload):
    b=bytearray(BLOCK)
    struct.pack_into("<II",b,0,MAGIC,0)
    nb=name.encode("ascii"); b[8:8+len(nb)]=nb
    struct.pack_into("<I",b,72,0)
    struct.pack_into("<I",b,76,1)
    struct.pack_into("<I",b,96,len(payload))
    b[100:100+len(payload)]=payload
    struct.pack_into("<I",b,ITEM_CRC_OFF,crc32(b[:ITEM_CRC_OFF]))
    return bytes(b)

def build_map(entries):
    m=bytearray(BLOCK); pos=0
    for name,size in entries:
        e=f"{name}:{size}".encode("ascii")+b"\0"
        if pos+len(e)>MAP_MAGIC_OFF:
            raise SystemExit("Map full")
        m[pos:pos+len(e)]=e; pos+=len(e)
    struct.pack_into("<I",m,MAP_MAGIC_OFF,MAGIC)
    struct.pack_into("<I",m,MAP_CRC_OFF,crc32(m[:MAP_CRC_OFF]))
    return bytes(m)

def patch(src,dst):
    data=bytearray(Path(src).read_bytes())
    entries=verify(bytes(data),False)
    sizes={s for _,s in entries}
    if sizes!={3176}:
        raise SystemExit(f"Refusing to guess map size token: {sizes}")
    existing={n for n,_ in entries}
    for name,payload in (("fastboot_status_flag",b"unlocked"),("device_unlock",b"unlock")):
        if name in existing:
            print(name,"already exists")
            continue
        idx=len(entries); off=2*BLOCK+idx*2*BLOCK
        item=build_item(name,payload)
        data[off:off+BLOCK]=item
        data[off+BLOCK:off+2*BLOCK]=item
        entries.append((name,3176)); existing.add(name)
        print(f"Added {name} at item {idx}, offsets 0x{off:x}/0x{off+BLOCK:x}")
    m=build_map(entries)
    data[:BLOCK]=m; data[BLOCK:2*BLOCK]=m
    Path(dst).write_bytes(data)
    print("Wrote",dst)
    verify(bytes(data),True)

def main():
    ap=argparse.ArgumentParser()
    sp=ap.add_subparsers(dest="cmd",required=True)
    v=sp.add_parser("verify"); v.add_argument("file"); v.add_argument("--require-unlock",action="store_true")
    p=sp.add_parser("patch"); p.add_argument("input"); p.add_argument("output")
    a=ap.parse_args()
    if a.cmd=="verify": verify(Path(a.file).read_bytes(),a.require_unlock)
    else: patch(a.input,a.output)

if __name__=="__main__":
    main()
