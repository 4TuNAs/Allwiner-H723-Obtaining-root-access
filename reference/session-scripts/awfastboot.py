import sys
import struct
import usb.core
import usb.util
import libusb_package

VID = 0x1F3A
PID = 0x1010

READ_ONLY_COMMANDS = [
    "getvar:product",
    "getvar:version",
    "getvar:current-slot",
    "getvar:secure",
    "getvar:unlocked",
    "getvar:max-download-size",

    # Проверяем, какие команды разрешены в secure mode
    "flashing get_unlock_ability",
    "oem device-info",
    "oem get-bootinfo",
    "oem get_unlock_ability",
]


def find_fastboot_device():
    backend = libusb_package.get_libusb1_backend()

    dev = usb.core.find(
        idVendor=VID,
        idProduct=PID,
        backend=backend
    )

    if dev is None:
        print(f"ERROR: USB device {VID:04x}:{PID:04x} not found")
        sys.exit(1)

    print(
        f"Found {dev.idVendor:04x}:{dev.idProduct:04x} "
        f"bus={dev.bus} address={dev.address}"
    )

    return dev


def read_usb_configuration(dev):
    # Читаем первые 9 байт CONFIGURATION descriptor
    head = bytes(
        dev.ctrl_transfer(
            0x80,       # Device -> Host, Standard
            0x06,       # GET_DESCRIPTOR
            0x0200,     # CONFIGURATION descriptor #0
            0,
            9,
            timeout=2000
        )
    )

    if len(head) < 9:
        raise RuntimeError(
            f"Short configuration descriptor: {head.hex()}"
        )

    total_length = struct.unpack_from("<H", head, 2)[0]
    config_value = head[5]

    raw = bytes(
        dev.ctrl_transfer(
            0x80,
            0x06,
            0x0200,
            0,
            total_length,
            timeout=2000
        )
    )

    print(
        f"Configuration value={config_value}, "
        f"length={len(raw)}"
    )

    return raw


def parse_interfaces(raw):
    interfaces = {}
    current_if = None

    pos = 0

    while pos + 2 <= len(raw):
        length = raw[pos]
        dtype = raw[pos + 1]

        if length < 2:
            break

        if pos + length > len(raw):
            break

        desc = raw[pos:pos + length]

        # USB_INTERFACE_DESCRIPTOR
        if dtype == 4 and length >= 9:
            interface_number = desc[2]
            alternate_setting = desc[3]
            interface_class = desc[5]
            interface_subclass = desc[6]
            interface_protocol = desc[7]

            current_if = interface_number

            interfaces[current_if] = {
                "alt": alternate_setting,
                "class": interface_class,
                "subclass": interface_subclass,
                "protocol": interface_protocol,
                "in": [],
                "out": [],
            }

        # USB_ENDPOINT_DESCRIPTOR
        elif dtype == 5 and length >= 7 and current_if is not None:
            endpoint_address = desc[2]
            attributes = desc[3]

            transfer_type = attributes & 0x03

            # Bulk endpoint
            if transfer_type == 2:
                if endpoint_address & 0x80:
                    interfaces[current_if]["in"].append(
                        endpoint_address
                    )
                else:
                    interfaces[current_if]["out"].append(
                        endpoint_address
                    )

        pos += length

    return interfaces


def find_fastboot_interface(interfaces):
    print("\nUSB interfaces:")

    for number, info in interfaces.items():
        print(
            f"IF {number}: "
            f"class={info['class']:02x} "
            f"sub={info['subclass']:02x} "
            f"proto={info['protocol']:02x} "
            f"OUT={[hex(x) for x in info['out']]} "
            f"IN={[hex(x) for x in info['in']]}"
        )

    # Сначала ищем именно стандартный Fastboot interface:
    # class FF / subclass 42 / protocol 03
    for number, info in interfaces.items():
        if (
            info["class"] == 0xFF
            and info["subclass"] == 0x42
            and info["protocol"] == 0x03
            and info["out"]
            and info["in"]
        ):
            return (
                number,
                info["out"][0],
                info["in"][0]
            )

    # Fallback: любой интерфейс с bulk OUT + IN
    for number, info in interfaces.items():
        if info["out"] and info["in"]:
            return (
                number,
                info["out"][0],
                info["in"][0]
            )

    raise RuntimeError(
        "No interface with bulk IN/OUT endpoints found"
    )


def fastboot(dev, ep_out, ep_in, command):
    print(f"\n> {command}")

    payload = command.encode("ascii")

    try:
        sent = dev.write(
            ep_out,
            payload,
            timeout=3000
        )

        print(f"sent {sent} bytes")

    except Exception as e:
        print("WRITE ERROR:", repr(e))
        return None

    while True:
        try:
            raw = bytes(
                dev.read(
                    ep_in,
                    256,
                    timeout=5000
                )
            )

        except usb.core.USBTimeoutError:
            print("< TIMEOUT waiting for response")
            return None

        except Exception as e:
            print("READ ERROR:", repr(e))
            return None

        text = raw.rstrip(b"\x00").decode(
            "utf-8",
            errors="replace"
        )

        print(f"< {text!r}")

        if len(text) < 4:
            continue

        prefix = text[:4]
        payload = text[4:]

        if prefix == "INFO":
            print(f"  INFO: {payload}")
            continue

        if prefix == "TEXT":
            print(f"  TEXT: {payload}")
            continue

        if prefix == "OKAY":
            return {
                "status": "OKAY",
                "data": payload
            }

        if prefix == "FAIL":
            return {
                "status": "FAIL",
                "data": payload
            }

        if prefix == "DATA":
            return {
                "status": "DATA",
                "data": payload
            }

        print(
            f"Unknown fastboot response prefix: "
            f"{prefix!r}"
        )


def main():
    dev = find_fastboot_device()

    try:
        raw_config = read_usb_configuration(dev)
        interfaces = parse_interfaces(raw_config)

        interface_number, ep_out, ep_in = (
            find_fastboot_interface(interfaces)
        )

        print(
            f"\nUsing interface {interface_number}: "
            f"OUT={ep_out:#04x}, IN={ep_in:#04x}"
        )

        # На Windows с WinUSB обычно достаточно claim_interface.
        try:
            usb.util.claim_interface(
                dev,
                interface_number
            )
        except usb.core.USBError as e:
            print(
                f"claim_interface warning: {e}"
            )

        print("\n=== READ-ONLY FASTBOOT TESTS ===")

        results = {}

        for command in READ_ONLY_COMMANDS:
            result = fastboot(
                dev,
                ep_out,
                ep_in,
                command
            )

            results[command] = result

        print("\n\n=== SUMMARY ===")

        for command, result in results.items():
            if result is None:
                print(
                    f"{command:30} -> NO RESPONSE"
                )
            else:
                print(
                    f"{command:30} -> "
                    f"{result['status']} "
                    f"{result['data']}"
                )

    finally:
        try:
            usb.util.release_interface(
                dev,
                interface_number
            )
        except Exception:
            pass

        try:
            usb.util.dispose_resources(dev)
        except Exception:
            pass


if __name__ == "__main__":
    main()