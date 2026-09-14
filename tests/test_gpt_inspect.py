import importlib.util
import struct
import sys
import unittest
import uuid
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gpt_inspect", ROOT / "scripts" / "gpt_inspect.py")
gpt = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gpt
spec.loader.exec_module(gpt)


def make_gpt():
    data = bytearray(34 * 512)
    data[510:512] = b"\x55\xaa"
    hdr = memoryview(data)[512:1024]
    hdr[:8] = b"EFI PART"
    struct.pack_into("<I", hdr, 8, 0x00010000)
    struct.pack_into("<I", hdr, 12, 92)
    struct.pack_into("<Q", hdr, 24, 1)
    struct.pack_into("<Q", hdr, 32, 9999)
    struct.pack_into("<Q", hdr, 40, 34)
    struct.pack_into("<Q", hdr, 48, 9900)
    hdr[56:72] = uuid.uuid4().bytes_le
    struct.pack_into("<Q", hdr, 72, 2)
    struct.pack_into("<I", hdr, 80, 128)
    struct.pack_into("<I", hdr, 84, 128)

    ent = memoryview(data)[1024:1152]
    ent[:16] = uuid.uuid4().bytes_le
    ent[16:32] = uuid.uuid4().bytes_le
    struct.pack_into("<Q", ent, 32, 100)
    struct.pack_into("<Q", ent, 40, 199)
    name = "boot_a".encode("utf-16-le")
    ent[56:56 + len(name)] = name

    array = bytes(data[1024:1024 + 128 * 128])
    struct.pack_into("<I", hdr, 88, zlib.crc32(array) & 0xFFFFFFFF)
    temp = bytearray(hdr[:92])
    struct.pack_into("<I", temp, 16, 0)
    struct.pack_into("<I", hdr, 16, zlib.crc32(temp) & 0xFFFFFFFF)
    return bytes(data)


class GPTTests(unittest.TestCase):
    def test_valid(self):
        meta, parts = gpt.parse_gpt(make_gpt())
        self.assertEqual(meta["entry_count"], 128)
        self.assertEqual(parts[0].name, "boot_a")
        self.assertEqual(parts[0].sectors, 100)

    def test_header_crc_rejected(self):
        data = bytearray(make_gpt())
        data[600] ^= 1
        with self.assertRaises(ValueError):
            gpt.parse_gpt(bytes(data))

    def test_array_crc_rejected(self):
        data = bytearray(make_gpt())
        data[1100] ^= 1
        with self.assertRaises(ValueError):
            gpt.parse_gpt(bytes(data))


if __name__ == "__main__":
    unittest.main()
