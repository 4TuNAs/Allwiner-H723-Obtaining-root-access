# Session script inventory

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
ASH_STANDALONE=1 \
BOOTMODE=true \
KEEPVERITY=true \
KEEPFORCEENCRYPT=true \
RECOVERYMODE=false \
./busybox sh ./boot_patch.sh ./init_boot_a.img
```

## Reconstructed utilities

The following utilities are kept separately because they are reconstructed workflow files rather than byte-for-byte original session scripts:

- `awfastboot_flash_initboot.py`
- `h723_secure_storage_tool.py`

They are stored under `reference/reconstructed/`.

## Documented boot sequence

The documented root procedure transitions the board to `UNLOCKED/ORANGE`, patches `init_boot_a` with Magisk, and flashes the patched `init_boot_a`. A separate `boot_a` kernel binary patch is not part of this documented procedure.
