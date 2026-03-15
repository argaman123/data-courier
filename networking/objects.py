import dataclasses, os, struct
from enum import Enum
from typing import Literal


@dataclasses.dataclass
class Packet:
    id: bytes
    type: Literal[0, 1, 2]
    index: int # size when type 0, and index when type 1
    payload: bytes

    @staticmethod
    def format() -> str:
        return '<8sBI'

    def to_bytes(self) -> bytes:
        return struct.pack(self.format(), self.id, self.type, self.index) + self.payload

    @staticmethod
    def from_bytes(data: bytes):
        header = data[:13]
        payload = data[13:]
        return Packet(*struct.unpack(Packet.format(), header), payload=payload)

class File:
    def __init__(self, path: str, _bytes: bytes, _id: bytes = None):
        self.path = path
        self.bytes = _bytes
        if _id is not None:
            self.id = _id
        else:
            self.id = os.urandom(8)

    def save(self, folder: str):
        with open(os.path.join(folder, self.path), 'wb') as f:
            f.write(self.bytes)
