# Documentation/code review notes

This public revision was rebuilt from the project conversation history, recovered session scripts, boot logs, the two board photos, and the binary captures supplied for the final review.

## Checks performed while preparing the repository

- Parsed `gpt34.bin` and verified both the GPT header CRC32 and partition-array CRC32.
- Reconstructed the exact 29-entry partition map from the supplied GPT dump.
- Parsed the supplied stock and Magisk-patched `init_boot_a` images as Android boot image v4 and verified their exact SHA-256 values, sizes and ramdisk-size change.
- Confirmed Magisk-specific markers are present in the patched image and absent in the stock image.
- Inspected `env_a.bin` for active slot and A/B partition-list strings.
- Inspected `toc1-area-2m.bin` for the Secure Storage unlock and orange-state implementation strings (`device_unlock`, `fastboot_status_flag`, `find fastboot unlock flag`, `orange`, verified-boot arguments).
- Inspected `boot0-primary-full.bin` for SBOOT/TOC1 boot-chain strings.
- Rechecked recovered pre-unlock and post-unlock UART evidence: the vbmeta digest remained the same while state changed from locked/green to unlocked/orange and `veritymode=enforcing` remained in place.
- Rechecked the recovered session scripts for GPT dumping, arbitrary UART dumping, Secure Storage patch/write, and Allwinner USB fastboot flashing.
- Searched the available project history/files specifically for the historical `boot_a` kernel-patch script/bytes. The exact artifact was not recovered and is therefore not fabricated in this repository.
- Removed device serial/MAC examples from public documentation.
- Added `.gitignore` rules to prevent accidental publication of raw firmware/dumps/logs.

## Public-script hardening

The public scripts under `scripts/` intentionally improve on the experimental session scripts:

- GPT CRC validation.
- Strict Base64 transfer handling.
- Exact Secure Storage unlock payload validation.
- Duplicate/bounds checks for Secure Storage items.
- Explicit SHA-256 gates for raw writes and fastboot flashes.
- Read-only/dry-run defaults.
- Explicit expected changed-block order required for the destructive Secure Storage write.
- Per-block and final full-image read-back verification.
- Last-boot-cycle parsing for AVB UART logs.

## Automated checks run locally

`python -m compileall -q scripts tests reference/session-scripts` completed successfully.

`python -m unittest discover -s tests -v` completed with **6/6 tests passing**:

- valid GPT accepted;
- GPT header CRC corruption rejected;
- GPT partition-array CRC corruption rejected;
- Secure Storage patch creates the exact `unlocked` / `unlock` values;
- an existing wrong unlock value is rejected;
- a corrupted item CRC is rejected.

The hardened `gpt_inspect.py` was also run against the supplied real `gpt34.bin`, and `init_boot_inspect.py` was run against both supplied real boot images.

## What could not be runtime-tested in this environment

This build environment does not have the physical H723 board attached, so the new serial/USB hardware wrappers cannot be re-executed end-to-end here. Their underlying historical operations are preserved in `reference/session-scripts/` and were used during the successful board session.

PowerShell itself is not installed in this build environment, so the `.ps1` helpers were reviewed statically rather than executed here.
