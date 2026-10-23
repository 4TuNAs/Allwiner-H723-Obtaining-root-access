# Tested board photographs

## V1.2 (original documented hardware)

- `h723-6621-v1.2-uart-location.jpg` — original photo marking the UART area.
- `h723-6621-v1.2-usb-adb-wiring.jpg` — original recovery USB-ADB and power wiring.

Both original V1.2 photos are retained without changes. Neither photo proves GND/TX/RX pin order.

## V1.3 — 23 October 2026

These **original user-uploaded files are already in this repository**. Do not upload duplicated or re-compressed copies to document this revision.

| Filename | Step / subject | Usage |
|---|---|---|
| `photo_6_2026-10-23_22-26-02.jpg` | Open H723 PCB, CP2102 UART serial attached | **Main V1.3 disassembly photo** |
| `photo_7_2026-10-23_22-26-02.jpg` | Mainboard wiring close-up | Hardware detail |
| `photo_8_2026-10-23_22-26-02.jpg` | Front panel / grille removed | Disassembly step |
| `photo_5_2026-10-23_22-26-02.jpg` | Android recovery menu | Recovery |
| `photo_4_2026-10-23_22-26-02.jpg` | Unlocked bootloader corruption warning | GREEN → ORANGE evidence |
| `photo_3_2026-10-23_22-26-02.jpg` | Android boot/recovery graphics | Boot sequence |
| `photo_2_2026-10-23_22-26-02.jpg` | Magisk "Requires additional setup" prompt | First patched boot |
| `photo_1_2026-10-23_22-26-02.jpg` | Magisk Superuser request for `com.android.shell` | Root authorization |
| `photo_9_2026-10-23_22-26-02.jpg` | Developer options: USB debugging enabled | ADB preparation |
| `photo_10_2026-10-23_22-26-02.jpg` | ADB RSA fingerprint authorization dialog | **Unredacted: don't embed until fingerprint blurred** |
| `photo_11_2026-10-23_22-26-02.jpg` | Developer options entry | Enabling developer features |
| `photo_12_2026-10-23_22-26-02.jpg` | Developer Tools app download | Alternative path to developer settings |

The screenshot with the ADB authorization prompt currently shows the computer's RSA key fingerprint. Although a public-key fingerprint is not a private key, the project owner requested that **only this string be blurred** before it is used in documentation. The original on `main` is not automatically sanitized by omitting its embed.

Please note: connection wire colors are not reliable pinout labels. Verify GND, RX, TX and the USB data/power lines on your own board.
