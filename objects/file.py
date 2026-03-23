import hashlib
import os
import struct
from pathlib import Path

class File:
    def __init__(self, path: Path):
        self.path = path
        self.id = os.urandom(8)
        header = self._encode_header()
        self.write_offset = len(header)
        self.bytearray = bytearray(self.write_offset + path.stat().st_size)
        self.bytearray[:self.write_offset] = header

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
        raw_bytes = memoryview(self.bytearray)
        if self.write_offset >= len(self.bytearray):
            for offset in range(0, len(self.bytearray), size):
                yield offset, raw_bytes[offset:offset + size]
        else:
            with self.path.open("rb") as file:
                while data := file.read(size - (self.write_offset % size)):
                    self.bytearray[self.write_offset:self.write_offset + len(data)] = data
                    offset = int(self.write_offset // size) * size
                    self.write_offset += len(data)
                    yield offset, raw_bytes[offset:self.write_offset]

    def __len__(self):
        return len(self.bytearray)

    def __str__(self):
        return self.path.name + f" [{self.id.hex()}]"

    # TODO <editor-fold desc="REMOVE CHECKSUM IN PROD">
    def checksum(self):
        return hashlib.sha256(self.extract_header(self.bytearray)[1]).digest()
    # TODO </editor-fold>
