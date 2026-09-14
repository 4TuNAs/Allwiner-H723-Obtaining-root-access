# Allwinner H723 Android root access — H723-6621-V1.2

This repository documents a **real rooting session** on an Android board based on **Allwinner H723 / sun50iw15p1**.

The board actually tested and photographed is **H723-6621-V1.2**. A board marked **H723-CY-4D308** looks very similar, but has **not** been verified here. Do not assume that its partition LBAs, Secure Storage contents, hashes, or boot images are identical.

> [!CAUTION]
> Parts of this procedure write raw eMMC sectors. A wrong LBA, wrong image, power loss, or using values from a different firmware can brick the board. Read and verify your own board first. The public scripts are deliberately read-only/dry-run by default wherever practical.

## Tested board

### UART area

![H723-6621-V1.2 UART location](images/h723-6621-v1.2-uart-location.jpg)

The photo identifies the UART connector area. It does **not** prove the exact GND/TX/RX order. Do not infer pin order from wire colors; verify it on your own PCB.

UART settings used during the work:

```text
115200 baud
8 data bits
no parity
1 stop bit
no flow control
```

### Recovery USB ADB wiring

![H723-6621-V1.2 recovery USB ADB wiring](images/h723-6621-v1.2-usb-adb-wiring.jpg)

This distinction is critical:

- network/TCP ADB can be used while normal Android is running;
- after `adb reboot recovery`, network ADB is no longer available on this board;
- recovery ADB requires the **physical USB data connection** soldered to the USB-A connector/data lines shown in the photo;
- UART remains connected in parallel for U-Boot/recovery logs and the raw eMMC tools.

The photo also marks the +5 V/GND points used in the test setup. Do not connect two 5 V sources together unless you have verified the power path on your board.

---

## Verified boot/root chain

```text
stock Android
    |
    | adb reboot recovery
    v
recovery
    |-- physical USB ADB
    `-- UART 115200 8N1
    |
    v
read + validate GPT
    |
    v
back up boot_a / init_boot_a / vendor_boot_a / vbmeta_a / misc / env_a
    |
    v
read Allwinner Secure Storage
    |
    v
add:
    device_unlock=unlock
    fastboot_status_flag=unlocked
    |
    v
rebuild CRCs + redundant copies
    |
    v
safe raw write + per-block read-back + final full read-back
    |
    v
U-Boot AVB state: LOCKED/GREEN -> UNLOCKED/ORANGE
    |
    v
separate kernel modification in boot_a
    |
    v
Magisk patch of init_boot_a
    |
    | adb reboot bootloader
    v
Allwinner USB fastboot 1f3a:1010
    |
    v
flash init_boot_a
    |
    v
Android -> magiskd -> su -> uid=0(root)
```

### Important historical gap

A separate kernel modification inside `boot_a` was part of the successful session **after the Secure Storage unlock and before the final Magisk boot**. The exact original patch script/byte sequence has not been recovered from the available project material, so this repository does not invent one or replace it with KernelSU/APatch/random hex edits. See [`docs/kernel-patch-status.md`](docs/kernel-patch-status.md).

Everything else below is backed by recovered session scripts, UART evidence and/or the supplied binary captures.

---

## 1. Host setup

Examples use Windows PowerShell because that is how the board was tested.

Install Android Platform Tools, Python 3, a 3.3 V USB-UART adapter, then:

```powershell
python -m pip install -r requirements.txt
```

For the Allwinner bootloader USB interface on Windows, PyUSB must be able to claim `1f3a:1010`; a libusb-compatible driver may be required.

Do not perform any raw write until UART works and backups exist.

---

## 2. Start in normal Android

Check ADB:

```powershell
.\adb.exe devices -l
```

Network ADB is acceptable **only at this stage**.

Save basic properties:

```powershell
.\adb.exe shell getprop ro.build.version.release
.\adb.exe shell getprop ro.build.version.sdk
.\adb.exe shell getprop ro.product.cpu.abi
.\adb.exe shell getprop ro.boot.slot_suffix
.\adb.exe shell getprop ro.boot.vbmeta.device_state
.\adb.exe shell getprop ro.boot.verifiedbootstate
.\adb.exe shell getprop ro.boot.veritymode
.\adb.exe shell uname -a
.\adb.exe shell getprop > getprop-stock.txt
```

Start UART capture before rebooting:

```powershell
python .\scripts\uart_log_capture.py COM5 --out boot-before-unlock.log
```

Use your actual COM port.

---

## 3. Enter recovery

From normal Android:

```powershell
.\adb.exe reboot recovery
```

If normal Android is reached through TCP ADB, target it explicitly:

```powershell
.\adb.exe -s 192.168.x.x:5555 reboot recovery
```

Once recovery starts, **do not wait for the old TCP endpoint to return**. Connect the physically soldered USB data wiring and check:

```powershell
.\adb.exe devices -l
.\adb.exe shell id
```

A helper is included:

```powershell
.\scripts\recovery_usb_adb.ps1 -Adb .\adb.exe -Target 192.168.x.x:5555
```

It requests recovery from normal Android and then waits for a **non-network** ADB serial. Keep UART connected in parallel.

---

## 4. Discover the partition table instead of guessing

The original session read the first 34 sectors from the recovery UART shell. The hardened equivalent is:

```powershell
python .\scripts\uart_dump.py COM5 --skip 0 --count 34 --out gpt34.bin
```

Validate and parse it:

```powershell
python .\scripts\gpt_inspect.py .\gpt34.bin
```

The parser verifies the MBR signature, `EFI PART`, GPT header CRC32, partition-array CRC32 and entry bounds.

For the supplied test-unit GPT:

```text
GPT header CRC32:       6ad342cd
partition array CRC32:  534057f5
entries:                29 x 128 bytes
```

Key partitions on the tested `_a` slot:

| Partition | Node on test unit | First LBA | Sectors | Size |
|---|---|---:|---:|---:|
| `env_a` | `mmcblk0p3` | 204800 | 512 | 256 KiB |
| `boot_a` | `mmcblk0p5` | 205824 | 131072 | 64 MiB |
| `vendor_boot_a` | `mmcblk0p7` | 467968 | 65536 | 32 MiB |
| `init_boot_a` | `mmcblk0p9` | 599040 | 16384 | 8 MiB |
| `misc` | `mmcblk0p12` | 5874688 | 32768 | 16 MiB |
| `vbmeta_a` | `mmcblk0p13` | 5907456 | 256 | 128 KiB |

The complete validated map is in [`docs/partition-map.md`](docs/partition-map.md).

Generate read-only backup commands from **your own GPT**:

```powershell
python .\scripts\gpt_inspect.py .\gpt34.bin --dump-plan COM5
```

Do not copy the tested unit's `mmcblk0pN` numbers to another firmware without parsing its GPT first.

---

## 5. Why `boot_a` and `init_boot_a` are different jobs

Recovered `env_a` data contains:

```text
slot_suffix=_a
ab_partition_list=bootloader,env,boot,vendor_boot,dtbo,vbmeta,vbmeta_system,vbmeta_vendor,init_boot,Reserve0
boot_fastboot=fastboot
```

The U-Boot log independently showed:

```text
partinfo: name boot_a, start 0x32400, size 0x20000
androidboot.slot_suffix=_a
ramdisk use init boot
pubkey vbmeta_a valid
```

Therefore:

- `_a` was the active slot;
- `boot_a` carried the kernel-side boot image that was modified separately;
- the generic ramdisk came from `init_boot_a`, making `init_boot_a` the Magisk target;
- `vbmeta_a`, `vendor_boot_a`, `misc` and `env_a` are important recovery/reference backups.

More detail: [`docs/boot-chain.md`](docs/boot-chain.md).

---

## 6. Back up stock partitions

Use LBAs from **your GPT**. Example for the tested `boot_a`:

```powershell
python .\scripts\uart_dump.py COM5 `
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

Create hashes:

```powershell
.\scripts\sha256_manifest.ps1 -Path . -OutFile .\SHA256SUMS-stock.txt
```

Keep another copy somewhere untouched.

---

## 7. Confirm the original LOCKED/GREEN state

Before the Secure Storage patch, UART showed:

```text
no item name device_unlock in the map
no item name fastboot_status_flag in the map
sunxi secure storage has no flag
androidboot.vbmeta.device_state=locked
androidboot.veritymode=enforcing
androidboot.verifiedbootstate=green
```

Analyze a saved boot log with:

```powershell
python .\scripts\avb_log_check.py .\boot-before-unlock.log
```

This establishes the baseline before writing anything.

---

## 8. Dump Allwinner Secure Storage

On the **tested H723-6621-V1.2 firmware**, the validated region was:

```text
start LBA: 12288
size:      256 sectors = 128 KiB
```

Read it first:

```powershell
python .\scripts\uart_dump.py COM5 `
  --skip 12288 `
  --count 256 `
  --out h723-secure-storage-original.bin
```

Test-unit original SHA-256:

```text
cc86b0255f07e9cec320285df83899a51354698c70003a8b1b1e56c807820490
```

> [!WARNING]
> LBA 12288 is verified for this test unit. On another board/firmware treat it as a read-only probe until the structure is validated. Never assume it is safe to write merely because the PCB looks similar.

Verify the structure:

```powershell
python .\scripts\secure_storage_tool.py verify .\h723-secure-storage-original.bin
```

The tool checks map/item magic, CRCs, bounds, duplicate names, and primary/backup copies.

---

## 9. Build the unlock candidate

```powershell
python .\scripts\secure_storage_tool.py patch `
  .\h723-secure-storage-original.bin `
  .\h723-secure-storage-unlocked.bin
```

The successful session added exactly:

```text
fastboot_status_flag = unlocked
device_unlock        = unlock
```

The hardened public tool verifies the **exact payloads**, not only the names.

Then:

```powershell
python .\scripts\secure_storage_tool.py verify `
  .\h723-secure-storage-unlocked.bin `
  --require-unlock
```

Test-unit candidate SHA-256:

```text
28a017814d6af136ab18f5f76396af4cd37f20cd407abfb613b0e4968c27fcc4
```

A different legitimate firmware can have different hashes. Do not use these hashes as a universal compatibility test.

---

## 10. Audit the live region before writing

Run the writer **without `--write` first**:

```powershell
python .\scripts\secure_storage_write_uart.py COM5 `
  .\h723-secure-storage-unlocked.bin `
  --secure-lba 12288 `
  --expected-live-sha256 cc86b0255f07e9cec320285df83899a51354698c70003a8b1b1e56c807820490 `
  --expected-candidate-sha256 28a017814d6af136ab18f5f76396af4cd37f20cd407abfb613b0e4968c27fcc4 `
  --backup-dir .\backup
```

This reads live Secure Storage, saves another backup, checks the exact source hash, compares source/candidate blocks, prints the safe commit order, and writes nothing.

For the successful test session the changed-block commit order was:

```text
8, 9, 10, 11, 1, 0
```

Item blocks are committed first, backup map next, primary map last.

---

## 11. Write the unlock flags

Only after the read-only audit matches exactly:

```powershell
python .\scripts\secure_storage_write_uart.py COM5 `
  .\h723-secure-storage-unlocked.bin `
  --secure-lba 12288 `
  --expected-live-sha256 cc86b0255f07e9cec320285df83899a51354698c70003a8b1b1e56c807820490 `
  --expected-candidate-sha256 28a017814d6af136ab18f5f76396af4cd37f20cd407abfb613b0e4968c27fcc4 `
  --expected-changed-blocks 8,9,10,11,1,0 `
  --backup-dir .\backup `
  --write
```

The writer performs preflight checks, writes only the expected changed 4 KiB blocks, `sync`s, immediately reads each block back byte-for-byte, then rereads and verifies the entire 128 KiB region. It does **not** reboot the board automatically.

If any read-back fails: **do not reboot**.

The exact historical writer is preserved in `reference/session-scripts/h723_secure_write_uart.py`.

---

## 12. Verify GREEN -> ORANGE

Keep UART recording and reboot only after the full write verification passes.

After the patch U-Boot saw:

```text
name in map device_unlock
name in map fastboot_status_flag
find fastboot unlock flag
```

and entered its orange path:

```text
Your device software can't be checked for corruption.
Please lock the bootloader.
orange state:start to display bootlogo
androidboot.vbmeta.device_state=unlocked
androidboot.veritymode=enforcing
androidboot.verifiedbootstate=orange
```

Check the saved log:

```powershell
python .\scripts\avb_log_check.py .\boot-after-unlock.log
```

The observed vbmeta digest stayed the same before and after this transition:

```text
8350ea2274ca1891b0dbd686b8254840b627e24ab72e8ce4211de492b6eb37c9
```

`veritymode` also remained `enforcing`.

So the working GREEN -> ORANGE transition did **not** require zeroing `vbmeta_a`, disabling dm-verity, installing Magisk, or patching the kernel merely to change the verified-boot state. It came from the two Allwinner Secure Storage flags consumed by U-Boot.

---

## 13. Kernel modification in `boot_a`

A distinct kernel modification happened here in the historical successful workflow:

```text
UNLOCKED / ORANGE
    -> patch kernel carried by boot_a
    -> boot-test patched kernel
    -> then patch init_boot_a with Magisk
```

The exact historical byte patch/tool is the one missing artifact. It is deliberately not guessed. See [`docs/kernel-patch-status.md`](docs/kernel-patch-status.md).

---

## 14. Patch `init_boot_a` with Magisk

The supplied stock image was independently verified as Android boot image v4:

```text
size:           8,388,608 bytes
header version: 4
kernel size:    0
ramdisk size:   3,346,935 bytes
SHA-256:        2d0b2683e03e3edea8e5e47426e23088e0f0da112f2c597ac84e6e400873dca0
```

The U-Boot line `ramdisk use init boot` is the evidence that `init_boot_a` is the Magisk ramdisk target on this firmware.

Inspect your image:

```powershell
python .\scripts\init_boot_inspect.py .\init_boot_a.img
```

Patch an **untouched copy of your own image** in Magisk:

```text
Magisk -> Install -> Select and Patch a File -> init_boot_a.img
```

The successful test-session result was:

```text
size:           8,388,608 bytes
header version: 4
kernel size:    0
ramdisk size:   3,240,383 bytes
SHA-256:        c1e41476e9cb34b4f7d1599b31f1f882d7b8257b03623020f5c02529e402bf91
```

The patched image contains Magisk markers (`/.magisk`, `PREINITDEVICE=`, `init-ld.xz`) absent from stock.

Do not download and flash this test-unit image onto another board; patch your own stock `init_boot_a`.

---

## 15. Enter Allwinner bootloader mode

From running Android:

```powershell
.\adb.exe reboot bootloader
```

On the tested unit the Allwinner USB interface used by the Python fastboot client was:

```text
VID:PID = 1f3a:1010
interface class/subclass/protocol = ff/42/03
```

This is a different phase from recovery ADB.

---

## 16. Dry-run the fastboot flash

For the exact test-session patched image:

```powershell
python .\scripts\awfastboot_flash.py `
  .\magisk_patched_init_boot_a.img `
  --partition init_boot_a `
  --size 8388608 `
  --sha256 c1e41476e9cb34b4f7d1599b31f1f882d7b8257b03623020f5c02529e402bf91
```

Without `--yes`, the script checks local SHA/size, locates `1f3a:1010` and `ff/42/03`, sends `getvar:max-download-size`, and writes nothing.

For your own freshly patched image, use the SHA-256 of **that exact file**.

---

## 17. Flash `init_boot_a`

After the dry-run succeeds:

```powershell
python .\scripts\awfastboot_flash.py `
  .\magisk_patched_init_boot_a.img `
  --partition init_boot_a `
  --size 8388608 `
  --sha256 <SHA256-OF-YOUR-EXACT-PATCHED-IMAGE> `
  --yes
```

The successful protocol sequence was:

```text
getvar:max-download-size
download:00800000
<8 MiB image data>
flash:init_boot_a
```

The script deliberately sends no reboot command after flashing.

---

## 18. Verify root

Boot Android normally and check:

```powershell
.\adb.exe devices
.\adb.exe shell "ps -A | grep magisk"
.\adb.exe shell "su -c 'id'"
```

The successful board showed a root-owned `magiskd` process and `su -c id` returned UID 0. The later `su` used during HDMI/capture experiments was therefore the result of the completed Magisk setup, not proof of factory root.

---

## Recovery checklist

Before the first destructive write keep offline copies of:

```text
gpt34.bin
env_a-stock.img
boot_a-stock.img
vendor_boot_a-stock.img
init_boot_a-stock.img
misc-stock.img
vbmeta_a-stock.img
h723-secure-storage-original.bin
SHA256SUMS-stock.txt
```

Do not casually write an entire image to `/dev/block/mmcblk0`. The successful Secure Storage procedure changed only the required 4 KiB blocks and verified each one immediately.

---

## H723-CY-4D308 and other similar boards

H723-CY-4D308 is listed because it looks very similar to the tested H723-6621-V1.2, **not** because binary compatibility has been proved.

Before reusing any destructive command on a similar board:

1. verify UART;
2. enter recovery and use physical USB ADB;
3. dump and validate its own GPT;
4. compare partition names/sizes;
5. dump its own stock boot images;
6. probe the candidate Secure Storage region read-only first;
7. require the Secure Storage parser to validate it;
8. compute hashes from that board;
9. patch its own `init_boot_a` with Magisk;
10. never flash an H723-6621-V1.2 image merely because the PCB looks similar.

---

## Scripts

Use `scripts/` for new work. They are publication-hardened: CRC/hash checks, strict transfer parsing, read-only/dry-run defaults and explicit write gates are added where possible.

`reference/session-scripts/` preserves the recovered experimental scripts actually used during the successful session for audit/history.

The public code was syntax-checked and the included unit suite passed **6/6 tests**. Details are in [`docs/review-notes.md`](docs/review-notes.md).

Raw firmware images/dumps are intentionally excluded by `.gitignore`. Verified artifact hashes and metadata are in [`docs/verified-artifacts.md`](docs/verified-artifacts.md).

## Current status

**Verified on H723-6621-V1.2:** GPT discovery, partition selection, Secure Storage unlock flags, `GREEN -> ORANGE`, Magisk `init_boot_a` characteristics, Allwinner USB fastboot path and final Magisk root.

**Not recovered:** the exact historical kernel patch applied to `boot_a` before the final Magisk step.

**Not tested:** H723-CY-4D308. It is only a visually similar board until independently validated.
