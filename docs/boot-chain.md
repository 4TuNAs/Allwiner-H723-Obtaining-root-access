# What was actually verified about the H723 boot chain

The test logs and supplied binary captures support the following chain:

```text
eMMC boot0 / SBOOT
    -> TOC1
    -> BL31 / OP-TEE / U-Boot 2018.07
    -> AVB verification of slot _a
    -> boot_a kernel
    -> init_boot_a generic ramdisk
    -> Android
```

Observed platform details include `sun50iw15p1`, Android 14 / API 34, a 32-bit userspace/kernel boot path, 1 GiB DRAM, and an ~7.46 GB eMMC.

`env_a` contains:

```text
slot_suffix=_a
ab_partition_list=bootloader,env,boot,vendor_boot,dtbo,vbmeta,vbmeta_system,vbmeta_vendor,init_boot,Reserve0
boot_fastboot=fastboot
boot_normal=sunxi_flash read 40007000 boot;bootm 40007000
boot_recovery=sunxi_flash read 40007000 recovery;bootm 40007000
```

The U-Boot log independently showed:

```text
partinfo: name boot_a, start 0x32400, size 0x20000
ramdisk use init boot
androidboot.slot_suffix=_a
```

This is why `boot_a` and `init_boot_a` must not be confused: `boot_a` is the kernel-side boot image and should be backed up, while Magisk modifies the generic ramdisk in `init_boot_a` on this firmware.

The captured TOC1/U-Boot area also contains the relevant implementation strings:

```text
device_unlock
fastboot_status_flag
find fastboot unlock flag
unlocked
orange_warning.bmp
orange state:start to display bootlogo
androidboot.verifiedbootstate=orange
androidboot.vbmeta.device_state=%s
```

That binary evidence agrees with the before/after UART logs and is why the guide describes the green-to-orange transition as an Allwinner Secure Storage / U-Boot state change, not as a `vbmeta`-zeroing trick.
