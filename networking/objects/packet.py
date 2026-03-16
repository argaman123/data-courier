import dataclasses
import struct
from typing import Literal


@dataclasses.dataclass
class Packet:
    id: bytes
    type: Literal[0, 1, 2]
    index: int # size when type 0, index when 1
    payload: bytes # filename when type 0, bytes when 1

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
