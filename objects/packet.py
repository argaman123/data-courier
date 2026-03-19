import struct

from objects.file import File


class Packet:
    format = '<8sBII'
    header_size = struct.calcsize(format)

    def __init__(self, _id: bytes, _type: int, offset: int, total_size: int, payload: bytes):
        self.id = _id
        self.type = _type
        self.offset = offset
        self.total_size = total_size
        self.payload = payload

    def __bytes__(self) -> bytes:
        return struct.pack(self.format, self.id, self.type, self.offset, self.total_size) + self.payload

    @staticmethod
    def from_bytes(data: bytes):
        header = data[:Packet.header_size]
        payload = data[Packet.header_size:]
        return Packet(*struct.unpack(Packet.format, header), payload=payload)

    def __str__(self):
        return f"[{self.id.hex()}]"


# TODO REMOVE CHECKSUM IN PRODUCTION
class Header(Packet):
    default_type = 0

    def __init__(self, _id: bytes, total_size: int, path: str, checksum: bytes):
        super().__init__(_id, self.default_type, 0, total_size, checksum + path.encode("utf-8"))
        self.path = path
        self.checksum = checksum

    @classmethod
    def from_file(cls, file: File):
        return cls(file.id, len(file.bytes), file.path, file.checksum)

    @classmethod
    def from_packet(cls, packet: Packet):
        return cls(packet.id, packet.total_size, packet.payload[32:].decode("utf-8"), packet.payload[:32])

class Payload(Packet):
    default_type = 1

    def __init__(self, _id: bytes, offset: int, total_size: int, payload: bytes):
        super().__init__(_id, self.default_type, offset, total_size, payload)

class End(Packet):
    default_type = 2
    default_id = b'\x00' * 8

    def __init__(self):
        super().__init__(self.default_id, self.default_type, 0, 0, b'')