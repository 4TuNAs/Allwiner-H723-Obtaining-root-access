# Kernel patch status

A separate modification of the kernel carried by `boot_a` was part of the successful rooting work **after** the Secure Storage unlock and **before** the final Magisk boot.

During this documentation pass, the project chats, uploaded files and File Library were searched specifically for:

- `boot_a` kernel patch scripts;
- hex offsets / before-and-after byte sequences;
- kernel `Image` patch commands;
- `magiskboot` kernel commands;
- `skip_initramfs` / `want_initramfs` changes;
- exact patch signatures and hashes.

The exact patch artifact or exact byte sequence was not recovered from the available material. This repository therefore does **not** substitute KernelSU, APatch, a random Allwinner patch, or an invented hex edit.

This is the only intentionally incomplete part of the historical reproduction. When the original patch is recovered, record at minimum:

```text
stock boot_a SHA-256
exact kernel extraction method
search signature / offset
original bytes
replacement bytes
repack method
patched boot_a SHA-256
exact flash/write command
UART result of the first patched-kernel boot
```

The Secure Storage green->orange procedure and the Magisk `init_boot_a` procedure are independently documented and verified; they should not be conflated with this missing kernel-patch artifact.
