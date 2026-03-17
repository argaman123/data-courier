import dataclasses
import struct
from typing import Literal

@dataclasses.dataclass
class Packet:
    id: bytes
    type: Literal[0, 1, 2]
    index: int
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

    def __str__(self):
        return f"[{self.id.hex()}]"


class Header(Packet):
    def __init__(self, _id: bytes, size: int, filename: str):
        super().__init__(_id, Header.default_type(), size, filename.encode("utf-8"))

    @property
    def file_name(self):
        return self.payload.decode("utf-8")

    @staticmethod
    def default_type():
        return 0

class Payload(Packet):
    def __init__(self, _id: bytes, index: int, payload: bytes):
        super().__init__(_id, Payload.default_type(), index, payload)

    @staticmethod
    def default_type():
        return 1

class End(Packet):
    def __init__(self, _id: bytes = bytes()):
        super().__init__(_id, End.default_type(), 0, bytes())

    @staticmethod
    def default_type():
        return 2