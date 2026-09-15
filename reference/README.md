# Reference material

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
