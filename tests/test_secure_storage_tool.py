import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sst", ROOT / "scripts" / "secure_storage_tool.py")
sst = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sst)


def make_image(items):
    data = bytearray(sst.TOTAL)
    entries = []
    for index, (name, payload) in enumerate(items):
        entries.append((name, 3176))
        block = sst.build_item(name, payload)
        off = 2 * sst.BLOCK + index * 2 * sst.BLOCK
        data[off:off + sst.BLOCK] = block
        data[off + sst.BLOCK:off + 2 * sst.BLOCK] = block
    map_block = sst.build_map(entries)
    data[:sst.BLOCK] = map_block
    data[sst.BLOCK:2 * sst.BLOCK] = map_block
    return bytes(data)


class SecureStorageTests(unittest.TestCase):
    def test_patch_adds_exact_values(self):
        original = make_image([("wifi_mac", b"00:00:00:00:00:00")])
        patched = sst.patch(original)
        _, items = sst.inspect(patched, require_unlock=True)
        self.assertEqual(items["fastboot_status_flag"]["payload"], b"unlocked")
        self.assertEqual(items["device_unlock"]["payload"], b"unlock")

    def test_wrong_existing_unlock_value_is_rejected(self):
        original = make_image([
            ("wifi_mac", b"00:00:00:00:00:00"),
            ("device_unlock", b"WRONG"),
        ])
        with self.assertRaises(ValueError):
            sst.patch(original)

    def test_corrupt_item_crc_is_rejected(self):
        data = bytearray(make_image([("wifi_mac", b"x")]))
        data[2 * sst.BLOCK + 200] ^= 1
        with self.assertRaises(ValueError):
            sst.inspect(bytes(data))


if __name__ == "__main__":
    unittest.main()
