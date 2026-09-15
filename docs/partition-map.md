# Verified GPT partition map — H723-6621-V1.2 test unit

This table was parsed from the validated 34-sector primary GPT capture. Both the GPT header CRC32 and partition-entry-array CRC32 validate successfully.

- GPT revision: `1.0`
- Header size: `92` bytes
- Primary header: LBA `1`
- Backup header: LBA `15269887`
- First usable LBA: `73728`
- Last usable LBA: `15269854`
- Partition entries: `29 x 128` bytes
- Header CRC32: `6ad342cd`
- Partition array CRC32: `534057f5`

The disk/partition GUIDs are intentionally omitted because they are per-device identifiers and are not required to reproduce the procedure.

| # | Linux node | Partition | First LBA | Last LBA | Sectors | Size |
|---:|---|---|---:|---:|---:|---:|
| 1 | `/dev/block/mmcblk0p1` | `bootloader_a` | 73728 | 139263 | 65536 | 32 MiB |
| 2 | `/dev/block/mmcblk0p2` | `bootloader_b` | 139264 | 204799 | 65536 | 32 MiB |
| 3 | `/dev/block/mmcblk0p3` | `env_a` | 204800 | 205311 | 512 | 256 KiB |
| 4 | `/dev/block/mmcblk0p4` | `env_b` | 205312 | 205823 | 512 | 256 KiB |
| 5 | `/dev/block/mmcblk0p5` | `boot_a` | 205824 | 336895 | 131072 | 64 MiB |
| 6 | `/dev/block/mmcblk0p6` | `boot_b` | 336896 | 467967 | 131072 | 64 MiB |
| 7 | `/dev/block/mmcblk0p7` | `vendor_boot_a` | 467968 | 533503 | 65536 | 32 MiB |
| 8 | `/dev/block/mmcblk0p8` | `vendor_boot_b` | 533504 | 599039 | 65536 | 32 MiB |
| 9 | `/dev/block/mmcblk0p9` | `init_boot_a` | 599040 | 615423 | 16384 | 8 MiB |
| 10 | `/dev/block/mmcblk0p10` | `init_boot_b` | 615424 | 631807 | 16384 | 8 MiB |
| 11 | `/dev/block/mmcblk0p11` | `super` | 631808 | 5874687 | 5242880 | 2560 MiB |
| 12 | `/dev/block/mmcblk0p12` | `misc` | 5874688 | 5907455 | 32768 | 16 MiB |
| 13 | `/dev/block/mmcblk0p13` | `vbmeta_a` | 5907456 | 5907711 | 256 | 128 KiB |
| 14 | `/dev/block/mmcblk0p14` | `vbmeta_b` | 5907712 | 5907967 | 256 | 128 KiB |
| 15 | `/dev/block/mmcblk0p15` | `vbmeta_system_a` | 5907968 | 5908095 | 128 | 64 KiB |
| 16 | `/dev/block/mmcblk0p16` | `vbmeta_system_b` | 5908096 | 5908223 | 128 | 64 KiB |
| 17 | `/dev/block/mmcblk0p17` | `vbmeta_vendor_a` | 5908224 | 5908351 | 128 | 64 KiB |
| 18 | `/dev/block/mmcblk0p18` | `vbmeta_vendor_b` | 5908352 | 5908479 | 128 | 64 KiB |
| 19 | `/dev/block/mmcblk0p19` | `frp` | 5908480 | 5909503 | 1024 | 512 KiB |
| 20 | `/dev/block/mmcblk0p20` | `empty` | 5909504 | 5940223 | 30720 | 15 MiB |
| 21 | `/dev/block/mmcblk0p21` | `metadata` | 5940224 | 5972991 | 32768 | 16 MiB |
| 22 | `/dev/block/mmcblk0p22` | `treadahead` | 5972992 | 6169599 | 196608 | 96 MiB |
| 23 | `/dev/block/mmcblk0p23` | `private` | 6169600 | 6202367 | 32768 | 16 MiB |
| 24 | `/dev/block/mmcblk0p24` | `dtbo_a` | 6202368 | 6206463 | 4096 | 2 MiB |
| 25 | `/dev/block/mmcblk0p25` | `dtbo_b` | 6206464 | 6210559 | 4096 | 2 MiB |
| 26 | `/dev/block/mmcblk0p26` | `media_data` | 6210560 | 6243327 | 32768 | 16 MiB |
| 27 | `/dev/block/mmcblk0p27` | `Reserve0_a` | 6243328 | 6276095 | 32768 | 16 MiB |
| 28 | `/dev/block/mmcblk0p28` | `Reserve0_b` | 6276096 | 6308863 | 32768 | 16 MiB |
| 29 | `/dev/block/mmcblk0p29` | `userdata` | 6308864 | 15269854 | 8960991 | ~4.27 GiB |

Do **not** assume this table applies to H723-CY-4D308 or another firmware. Run `scripts/uart_dump.py` + `scripts/gpt_inspect.py` first and use the LBAs from that device.
