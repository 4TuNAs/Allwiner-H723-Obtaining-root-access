# Scripts

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
