import struct

from objects.file import File


class Packet:
    format = '<B8sIBBIB'
    header_size = struct.calcsize(format)

    def __init__(self, _type: int, file_id: bytes, file_size: int,
                 k: int, m: int,
                 chunk_index: int, packet_index: int, payload: bytes):
        self.type = _type
        self.file_id = file_id
        self.file_size = file_size
        self.k = k
        self.m = m
        self.chunk_index = chunk_index
        self.packet_index = packet_index
        self.payload = payload

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


# TODO REMOVE CHECKSUM IN PRODUCTION
class Header(Packet):
    default_type = 0

    def __init__(self, file_id: bytes, file_size: int, path: str, checksum: bytes):
        super().__init__( self.default_type, file_id, file_size, 0, 0, 0, 0, checksum + path.encode("utf-8"))
        self.path = path
        self.checksum = checksum

    @classmethod
    def from_file(cls, file: File):
        return cls(file.id, len(file.bytes), file.path, file.checksum)

    @classmethod
    def from_packet(cls, packet: Packet):
        return cls(packet.file_id, packet.file_size, packet.payload[32:].decode("utf-8"), packet.payload[:32])

class Payload(Packet):
    default_type = 1

    def __init__(self, file_id: bytes, file_size: int, k: int, m: int, chunk_index: int, packet_index: int,payload: bytes):
        super().__init__(self.default_type, file_id, file_size, k, m, chunk_index, packet_index, payload)

# TODO REMOVE END PACKET IN PRODUCTION
class End(Packet):
    default_type = 2
    default_id = b'\x00' * 8

    def __init__(self):
        super().__init__(self.default_type, self.default_id, 0, 0, 0, 0, 0, b'')