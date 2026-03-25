import dataclasses
import struct
from typing import ClassVar


@dataclasses.dataclass
class Packet:
    file_id: bytes
    file_size: int
    k: int
    m: int
    chunk_index: int
    packet_index: int
    payload: bytes

    # noinspection SpellCheckingInspection
    format: ClassVar[str] = '<8sQBBIB'
    header_size: ClassVar[int] = struct.calcsize(format)

    def __bytes__(self) -> bytes:
        return (struct.pack(self.format, self.file_id, self.file_size, self.k - 1, self.m - 1, self.chunk_index, self.packet_index)
                + self.payload)

    @staticmethod
    def from_bytes(data: bytes):
        header = data[:Packet.header_size]
        payload = data[Packet.header_size:]
        packet = Packet(*struct.unpack(Packet.format, header), payload=payload)
        packet.k += 1
        packet.m += 1
        return packet

    def __str__(self):
        return f"[{self.file_id.hex()}]"

    def __len__(self):
        return self.header_size + len(self.payload)