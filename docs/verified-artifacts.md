# Verified artifacts from the test session

Raw firmware/dump files are intentionally **not** included in this repository. The hashes below document exactly what was inspected while preparing the guide.

| Artifact | Size | SHA-256 | Notes |
|---|---:|---|---|
| `gpt34.bin` | 17,408 B | `92708ad2bf46dd9742c49b9139223dab8af369ecc2f384d20d387248d3ef84fb` | Primary GPT capture; both CRCs valid |
| `toc1-area-2m.bin` | 2,097,152 B | `7c7683485cb84a12e672053a32c59b4978ef0fbf0dc507febe6957d2b441df87` | Contains the U-Boot/TOC1 unlock/orange-state strings used as corroborating evidence |
| `env_a.bin` | 262,144 B | `f6a540a3297f9087bb2af7f11b49c003bf75f22e684b98cb32fa34244f87c70d` | Contains `slot_suffix=_a` and the A/B partition list |
| `boot0-primary-full.bin` | 77,824 B | `3ef9be3f1e330cfd714283191fa1875db2898255ff2ad9682a5228113d03434c` | SBOOT/TOC0 sample from the test unit |
| `init_boot_a.img` | 8,388,608 B | `2d0b2683e03e3edea8e5e47426e23088e0f0da112f2c597ac84e6e400873dca0` | Stock Android boot image v4; ramdisk size 3,346,935 B |
| `magisk_patched_init_boot_a.img` | 8,388,608 B | `c1e41476e9cb34b4f7d1599b31f1f882d7b8257b03623020f5c02529e402bf91` | Patched Android boot image v4; Magisk markers present; ramdisk size 3,240,383 B |

## Secure Storage hashes from the successful unlock session

These came from the exact H723-6621-V1.2 test unit and are deliberately hard-coded only in the original session writer, not in the generic public writer.

- Original 128 KiB region: `cc86b0255f07e9cec320285df83899a51354698c70003a8b1b1e56c807820490`
- Unlocked candidate: `28a017814d6af136ab18f5f76396af4cd37f20cd407abfb613b0e4968c27fcc4`
- Tested Secure Storage start: LBA `12288`
- Tested size: `256` sectors / `128 KiB`
- Successful commit order in that session: `8, 9, 10, 11, 1, 0`

Do not use these hashes as a compatibility test for a different board. A different legitimate firmware image is expected to have different hashes.
