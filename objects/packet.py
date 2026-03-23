import dataclasses
import struct
from typing import ClassVar


@dataclasses.dataclass
class Packet:
    # TODO <editor-fold desc="REMOVE TYPE IN PROD">
    type: int
    # TODO </editor-fold>
    file_id: bytes
    file_size: int
    k: int
    m: int
    chunk_index: int
    packet_index: int
    payload: bytes

    # noinspection SpellCheckingInspection
    format: ClassVar[str] = '<B8sIBBIB'
    header_size: ClassVar[int] = struct.calcsize(format)

    def __bytes__(self) -> bytes:
        return (struct.pack(self.format, self.type, self.file_id, self.file_size, self.k, self.m, self.chunk_index, self.packet_index)
                + self.payload)

    @staticmethod
    def from_bytes(data: bytes):
        header = data[:Packet.header_size]
        payload = data[Packet.header_size:]
        return Packet(*struct.unpack(Packet.format, header), payload=payload)

    def __str__(self):
        return f"[{self.file_id.hex()}]"


# TODO <editor-fold desc="REMOVE END IN PROD">
class End(Packet):
    default_type = 1
    default_id = b'\x00' * 8

    def __init__(self):
        super().__init__(self.default_type, self.default_id, 0, 0, 0, 0, 0, b'')
# TODO </editor-fold>