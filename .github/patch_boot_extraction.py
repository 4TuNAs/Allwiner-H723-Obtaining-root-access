from pathlib import Path

p = Path('README.md')
s = p.read_text()

old = '''# 6. Back up the stock partitions

Use the LBAs printed by **your** GPT. Example for the tested `boot_a`:

```powershell
python .\\scripts\\uart_dump.py COM5 `
  --skip 205824 `
  --count 131072 `
  --out boot_a-stock.img
```

Back up at least:

```text
env_a
boot_a
vendor_boot_a
init_boot_a
misc
vbmeta_a
```

Generate a hash manifest:

```powershell
.\\scripts\\sha256_manifest.ps1 -Path . -OutFile .\\SHA256SUMS-stock.txt
```

Store a second copy somewhere that will not be modified during the experiment.
'''

new = '''# 6. Extract the stock boot images and back up the partitions

This is the point where the boot images are actually copied from eMMC to the PC. Do this **after** reading/validating the GPT and **before** any Secure Storage or boot-image modification.

On this board there are two different images that are easy to confuse:

- `boot_a` — 64 MiB kernel-side boot image;
- `init_boot_a` — 8 MiB Android boot v4 image containing the generic ramdisk. **This is the image later patched by Magisk.**

The tested GPT gives:

```text
boot_a:      first LBA 205824, sectors 131072
init_boot_a: first LBA 599040, sectors 16384
```

## 6.1 Extract `boot_a`

Using the publication-hardened dumper:

```powershell
python .\\scripts\\uart_dump.py COM5 `
  --skip 205824 `
  --count 131072 `
  --out boot_a-stock.img
```

The original session tool that performs the same `dd if=/dev/block/mmcblk0 ... | base64` transfer is preserved as `reference/session-scripts/uartdump.py`.

Expected size for this tested GPT:

```text
131072 * 512 = 67108864 bytes = 64 MiB
```

## 6.2 Extract the stock `init_boot_a` used for Magisk

This is the missing transition between partition discovery and the later Magisk step:

```powershell
python .\\scripts\\uart_dump.py COM5 `
  --skip 599040 `
  --count 16384 `
  --out init_boot_a-stock.img
```

Expected size:

```text
16384 * 512 = 8388608 bytes = 8 MiB
```

For the tested unit, the extracted stock image was verified as:

```text
SHA-256:
2d0b2683e03e3edea8e5e47426e23088e0f0da112f2c597ac84e6e400873dca0
```

Keep `init_boot_a-stock.img` untouched as the recovery copy. Create the working input for Magisk from that verified dump:

```powershell
Copy-Item .\\init_boot_a-stock.img .\\init_boot_a.img
Get-FileHash .\\init_boot_a.img -Algorithm SHA256
```

The copy must still be exactly 8,388,608 bytes and, on the tested unit, must still have the SHA-256 shown above.

## 6.3 Back up the remaining relevant partitions

Do the same for at least:

```text
env_a
vendor_boot_a
misc
vbmeta_a
```

Use the LBAs and sector counts printed from **your own GPT**. You can generate the read-only commands automatically:

```powershell
python .\\scripts\\gpt_inspect.py .\\gpt34.bin --dump-plan COM5
```

At the end of this stage you should have at minimum:

```text
boot_a-stock.img
init_boot_a-stock.img
vendor_boot_a-stock.img
vbmeta_a-stock.img
misc-stock.img
env_a-stock.img
```

Generate a hash manifest:

```powershell
.\\scripts\\sha256_manifest.ps1 -Path . -OutFile .\\SHA256SUMS-stock.txt
```

Store a second copy somewhere that will not be modified during the experiment. Do not continue until the 8 MiB `init_boot_a` dump has been verified, because that exact image is the source for the Magisk patch later in this guide.
'''

if old not in s:
    raise SystemExit('Target section was not found; refusing to modify README')

p.write_text(s.replace(old, new, 1))
