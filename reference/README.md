# Reference material

This directory separates **exact archived session files** from files reconstructed later from chat/project material.

## `session-scripts/`

These files are byte-for-byte copies extracted from the uploaded `platform-tools.rar` working-directory archive:

- `py.py` — early SBOOT UART helper that waits for `HELLO! SBOOT is starting!` and repeatedly sends `2` during the short boot0/SBOOT window.
- `awfastboot.py` — read-only PyUSB fastboot probe for Allwinner `1f3a:1010`; it issues only `getvar`/`oem`/unlock-ability queries.
- `uart_gpt.py` — dumps and parses the first 34 eMMC sectors through the UART recovery shell.
- `uartdump.py` — generic read-only eMMC LBA dumper through the UART recovery shell.
- `h723_secure_write_uart.py` — the exact safeguarded Secure Storage writer from the working directory.

See [`../docs/session-script-inventory.md`](../docs/session-script-inventory.md) for hashes and external Magisk scripts that were also present in the archive.

## `chat-recovered/`

Files in this directory were recovered/reconstructed from chat/project material but were **not present as files in the uploaded `platform-tools.rar` archive**. They are retained for audit/history and must not be described as byte-for-byte archived session files.
