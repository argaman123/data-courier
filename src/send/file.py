import os
import struct
from pathlib import Path

from src.common.config import settings


class File:
    caching_enabled = settings.get('sender', {}).get('enable_file_caching', False)

    def __init__(self, path: str, folder: Path):
        self.path = path
        self.file = folder / path
        self.id = os.urandom(8)
        self.header = self._encode_header()
        self.size = len(self.header) + self.file.stat().st_size
        self.cached = False
        if self.caching_enabled:
            self.bytearray = bytearray(self.size)

    def _encode_header(self):
        name_bytes = str(self.path).encode("utf-8")
        return struct.pack(f'<H{len(name_bytes)}s', len(name_bytes), name_bytes)

    @staticmethod
    def extract_header(full_bytes: bytearray):
        raw_bytes = memoryview(full_bytes)
        name_length = struct.unpack('<H', raw_bytes[:2])[0]
        path = bytes(raw_bytes[2:2 + name_length]).decode("utf-8")
        return path, raw_bytes[2 + name_length:]

    def read(self, size: int):
        if self.cached:
            raw_bytes = memoryview(self.bytearray)
            for offset in range(0, len(self.bytearray), size):
                yield offset, raw_bytes[offset:offset + size]
        else:
            offset = 0
            with self.file.open("rb") as file:
                data = self.header + file.read(size - len(self.header))
                while data:
                    yield offset, data
                    if self.caching_enabled:
                        self.bytearray[offset:offset + len(data)] = data
                    offset += len(data)
                    data = file.read(size)
            if self.caching_enabled:
                self.cached = True

    def __len__(self):
        return self.size

    def __str__(self):
        return str(self.path) + f" [{self.id.hex()}]"
