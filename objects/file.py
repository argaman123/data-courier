import hashlib
import os
import struct
from pathlib import Path

class File:
    def __init__(self, path: Path):
        self.path = path
        self.id = os.urandom(8)
        self.header = self._encode_header()

    def _encode_header(self):
        name_bytes = self.path.name.encode("utf-8")
        return struct.pack(f'<H{len(name_bytes)}s', len(name_bytes), name_bytes)

    @staticmethod
    def extract_header(full_bytes: bytearray):
        raw_bytes = memoryview(full_bytes)
        name_length = struct.unpack('<H', raw_bytes[:2])[0]
        path = bytes(raw_bytes[2:2 + name_length]).decode("utf-8")
        return path, raw_bytes[2 + name_length:]

    def read(self, size: int):
        offset = 0
        with self.path.open("rb") as file:
            data = self.header + file.read(size - len(self.header))
            while data:
                yield offset, data
                offset += len(data)
                data = file.read(size)

    def __len__(self):
        return len(self.header) + self.path.stat().st_size

    def __str__(self):
        return self.path.name + f" [{self.id.hex()}]"

    # TODO <editor-fold desc="REMOVE CHECKSUM IN PROD">
    def checksum(self):
        return hashlib.sha256(self.path.read_bytes()).digest()
    # TODO </editor-fold>
