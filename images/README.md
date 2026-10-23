# Tested board photographs

## V1.2 (original documented hardware)

- `h723-6621-v1.2-uart-location.jpg` — original photo marking the UART area.
- `h723-6621-v1.2-usb-adb-wiring.jpg` — original recovery USB-ADB and power wiring.

Both original V1.2 photos are retained without changes. Neither photo proves GND/TX/RX pin order.

## V1.3 — 23 October 2026

These **original user-uploaded files are already in this repository**. Do not upload duplicated or re-compressed copies to document this revision.

| Filename | Step / subject | Usage |
|---|---|---|
| `h723-6621-v1.3-open-mainboard-cp2102.jpg` | Open H723 PCB, CP2102 UART serial attached | **Main V1.3 disassembly photo** |
| `h723-6621-v1.3-mainboard-uart-wiring-closeup.jpg` | Mainboard wiring close-up | Hardware detail |
| `h723-6621-v1.3-front-grille-removed.jpg` | Front panel / grille removed | Disassembly step |
| `h723-6621-v1.3-android-recovery-menu.jpg` | Android recovery menu | Recovery |
| `h723-6621-v1.3-unlocked-bootloader-warning.jpg` | Unlocked bootloader corruption warning | GREEN → ORANGE evidence |
| `h723-6621-v1.3-android-boot-logo.jpg` | Android boot/recovery graphics | Boot sequence |
| `h723-6621-v1.3-magisk-additional-setup.jpg` | Magisk "Requires additional setup" prompt | First patched boot |
| `h723-6621-v1.3-magisk-superuser-authorization.jpg` | Magisk Superuser request for `com.android.shell` | Root authorization |
| `h723-6621-v1.3-usb-debugging-enabled.jpg` | Developer options: USB debugging enabled | ADB preparation |
| `h723-6621-v1.3-adb-rsa-authorization.jpg` | ADB RSA fingerprint authorization dialog | Original image retained, RSA fingerprint visible |
| `h723-6621-v1.3-developer-options-menu.jpg` | Developer options entry | Enabling developer features |
| `h723-6621-v1.3-developer-tools-play-store.jpg` | Developer Tools app download | Alternative path to developer settings |

The USB debugging authorization photograph shows the computer's **RSA public-key fingerprint**, not a private key. It remains unblurred at the owner's request. The photo files were renamed without recompression or modification; original image blob SHA values are preserved.

Please note: connection wire colors are not reliable pinout labels. Verify GND, RX, TX and the USB data/power lines on your own board.
