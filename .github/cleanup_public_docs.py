from pathlib import Path
import re

# Main README: keep only public technical facts and reproducibility information.
p = Path('README.md')
s = p.read_text()
s = re.sub(
    r'(Android -> magiskd -> su -> uid=0\(root\)\n```\n\n)### .*?\n\n.*?\n---\n\n# 1\. Host setup',
    r'\1### Reproducibility note\n\nThe documented root path is: **unlock the Allwinner boot state through Secure Storage, verify `LOCKED/GREEN -> UNLOCKED/ORANGE`, then patch `init_boot_a` with Magisk and flash the patched `init_boot_a`.**\n\nOriginal session scripts, reconstructed utilities, and publication-hardened tools are kept in separate directories so their roles are clear. See [`docs/session-script-inventory.md`](docs/session-script-inventory.md).\n\n---\n\n# 1. Host setup',
    s,
    count=1,
    flags=re.S,
)
s = re.sub(
    r'continue with the stock `init_boot_a` image\. .*?\n\n`boot_a` should still be backed up',
    'continue with the stock `init_boot_a` image. A separate `boot_a` kernel binary patch is not part of the documented root procedure.\n\n`boot_a` should still be backed up',
    s,
    count=1,
    flags=re.S,
)
s = s.replace('Detailed review/test notes are in [`docs/review-notes.md`](docs/review-notes.md).\n', '')
s = re.sub(
    r'│   └── [^/\n]+/\n│       └── .*files reconstructed.*',
    '│   └── reconstructed/\n│       └── ... reconstructed utilities kept separately from original session scripts ...',
    s,
)
s = re.sub(
    r'\nThe original .*?publication-hardened replacements remain under `scripts/`\.',
    '\nOriginal session scripts are preserved under `reference/session-scripts/`; reconstructed utilities are under `reference/reconstructed/`; publication-hardened tools remain under `scripts/`.',
    s,
    count=1,
    flags=re.S,
)
s = re.sub(
    r'The exact first discovery experiment that originally led us to LBA 12288 .*?\n',
    'The exact first discovery method for LBA 12288 is not documented here. The location itself is confirmed by the successful dump/write sequence and subsequent boot behavior, so this guide does not invent an unverified discovery command.\n',
    s,
    count=1,
)
p.write_text(s)

Path('scripts/README.md').write_text('''# Scripts

Use the files in this directory for new/repeated work. These are publication-hardened versions of the workflow: destructive actions are opt-in, hashes/CRCs are checked, and board-specific assumptions must be supplied explicitly where practical.

- `uart_log_capture.py` — capture UART output to a file.
- `uart_dump.py` — strict read-only raw eMMC dump through the recovery UART shell.
- `gpt_inspect.py` — validate primary GPT CRCs and print partition LBAs.
- `secure_storage_tool.py` — validate/patch the observed Allwinner Secure Storage structure.
- `secure_storage_write_uart.py` — hash-gated, read-back-verified Secure Storage writer; read-only unless `--write`.
- `avb_log_check.py` — summarize the last SBOOT/U-Boot cycle and its AVB state.
- `init_boot_inspect.py` — inspect Android boot v3/v4 headers and common Magisk markers.
- `awfastboot_flash.py` — SHA-gated Allwinner USB fastboot client; dry-run unless `--yes`.
- `recovery_usb_adb.ps1` — normal-Android -> recovery helper that deliberately waits for physical USB ADB rather than the old network endpoint.
- `sha256_manifest.ps1` — produce a SHA-256 manifest of backups.

These are **publication-hardened tools**, not a claim that every file in this directory existed during the original rooting session.

The original session scripts are preserved under `reference/session-scripts/`. See [`../docs/session-script-inventory.md`](../docs/session-script-inventory.md) for SHA-256 values and roles. Prefer the hardened versions here for new work.
''')

Path('reference/README.md').write_text('''# Reference material

This directory separates **original session scripts** from utilities reconstructed later for documentation/reproducibility.

## `session-scripts/`

These files are byte-for-byte preserved copies of the scripts used during the original H723 work:

- `py.py` — early SBOOT UART helper that waits for `HELLO! SBOOT is starting!` and repeatedly sends `2` during the short boot0/SBOOT window.
- `awfastboot.py` — read-only PyUSB fastboot probe for Allwinner `1f3a:1010`; it issues only `getvar`/`oem`/unlock-ability queries.
- `uart_gpt.py` — dumps and parses the first 34 eMMC sectors through the UART recovery shell.
- `uartdump.py` — generic read-only eMMC LBA dumper through the UART recovery shell.
- `h723_secure_write_uart.py` — safeguarded Secure Storage writer used for the tested board.

See [`../docs/session-script-inventory.md`](../docs/session-script-inventory.md) for hashes and descriptions.

## `reconstructed/`

These files were reconstructed from the documented workflow and retained separately so they are not confused with byte-for-byte original session scripts.
''')

Path('reference/session-scripts/README.md').write_text('''# Original session scripts

The files in this directory are byte-for-byte preserved copies of scripts used during the original H723 work. Do not confuse them with the safer publication versions under `../../scripts/`.

See [`../../docs/session-script-inventory.md`](../../docs/session-script-inventory.md) for SHA-256 values and descriptions.
''')

Path('docs/session-script-inventory.md').write_text('''# Session script inventory

The files under `reference/session-scripts/` are byte-for-byte preserved copies of original session scripts.

## Original session scripts

| File | Size | SHA-256 | Role in the session |
|---|---:|---|---|
| `py.py` | 1,786 B | `96ccf4ee1e7ad98b7cfd7cff821ee8ef23755da73000e91a1a038b0ae61fda79` | Opens COM5 at 115200, waits for the SBOOT banner, and repeatedly sends `2` during the short early-boot input window. |
| `awfastboot.py` | 8,301 B | `62c95cc51571aafb97f3531b05ed3f10b282b57e351ee6c564e612ed21e74ebf` | Read-only PyUSB fastboot probe for VID:PID `1f3a:1010`; inspects descriptors/interfaces and sends only read-only `getvar`/`oem` queries. |
| `uartdump.py` | 6,211 B | `d2f26b5c22b1549ff23e8eb0c9ff8ba8fbd2cf53cf0d3ca99a972dc33f12f29a` | Generic read-only raw eMMC dump by LBA through the recovery UART shell using `dd | base64`. |
| `uart_gpt.py` | 5,100 B | `790eb6b1e579f35c3a895d38841572b1c44add2db6b741211e4086a76a1690f8` | Reads LBA 0..33, saves `gpt34.bin`, validates GPT signature, and prints the partition map. |
| `h723_secure_write_uart.py` | 12,620 B | `9513e0e49723d7e48a4f821f05db0858168f10c7408ddafbc291647e0022effb` | Hash-gated Secure Storage writer for the tested board, with backup, six-block commit order and per-block/full read-back. |

All five Python files above pass Python syntax compilation.

## Magisk scripts used by the patch workspace

These are upstream Magisk files, not project-authored scripts. They are listed for reproducibility rather than copied into `reference/session-scripts/` as project code.

| File | Size | SHA-256 |
|---|---:|---|
| `magisk_patch/boot_patch.sh` | 7,197 B | `20de7208d610a267aaafafe09846c4458a240ba51656d05252fc1c9c7e7ada8f` |
| `magisk_patch/util_functions.sh` | 20,418 B | `01c392c8fe1a0da584f85a3738f3f0a19b73e120408ca6f4795027538aad6077` |

The Magisk patch workspace also contains `busybox`, `magiskboot`, `magiskinit`, `init-ld`, `magisk`, and `stub.apk`. The documented manual patch command is:

```sh
ASH_STANDALONE=1 \\
BOOTMODE=true \\
KEEPVERITY=true \\
KEEPFORCEENCRYPT=true \\
RECOVERYMODE=false \\
./busybox sh ./boot_patch.sh ./init_boot_a.img
```

## Reconstructed utilities

The following utilities are kept separately because they are reconstructed workflow files rather than byte-for-byte original session scripts:

- `awfastboot_flash_initboot.py`
- `h723_secure_storage_tool.py`

They are stored under `reference/reconstructed/`.

## Documented boot sequence

The documented root procedure transitions the board to `UNLOCKED/ORANGE`, patches `init_boot_a` with Magisk, and flashes the patched `init_boot_a`. A separate `boot_a` kernel binary patch is not part of this documented procedure.
''')

p = Path('docs/verified-artifacts.md')
s = p.read_text().replace('hard-coded only in the archived session writer', 'hard-coded only in the original session writer')
p.write_text(s)

p = Path('docs/partition-map.md')
s = p.read_text().replace('This table was parsed from the uploaded 34-sector primary GPT dump.', 'This table was parsed from the validated 34-sector primary GPT capture.')
p.write_text(s)

old = Path('reference/chat-recovered')
new = Path('reference/reconstructed')
if old.exists() and not new.exists():
    old.rename(new)

Path('docs/review-notes.md').unlink(missing_ok=True)
