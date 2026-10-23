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

## H723-6621-V1.3 independently verified (23 October 2026)

| Artifact | Size | SHA-256 | Notes |
|---|---:|---|---|
| `gpt34.bin` | 17,408 B | `b852badd4d159cdca67d3bf2acd86feaa0a18bffe87a310666206d4fb8843e05` | Both GPT CRCs matched V1.2, 29 partitions |
| `init_boot_a-stock.img` | 8,388,608 B | `624a3a0609ecbc7650d8371e73c5542397923f9e0a23c15e85f3342606a0319c` | Boot header v4, ramdisk 3,346,955 B |
| `magisk_patched_init_boot_a.img` | 8,388,608 B | `e9e9015493ecfa35f77dc5d79363c745033ab9b695a0be47a1b53f0a06898331` | Magisk 30.7 offline ARM32 patch, ramdisk 3,281,800 B |
| Secure Storage original | 131,072 B | `277f5e0163c2bae1f26975215543c3c9998f8b2b9f851a030dcf154d12e7bedc` | LBA 12288; parser PASS |
| Secure Storage unlocked | 131,072 B | `3ce01845d4d90e3322d4fb03939d1fd7996f7ad4af2ec096716a39e4df9612c6` | Write and full read-back PASS; commit order 8,9,10,11,1,0 |

**No `boot_a` dump was made on V1.3; it is not needed for the root workflow.** See [V1.3 root session](h723-6621-v1.3-verified-root.md).
