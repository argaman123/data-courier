import dataclasses, struct
from networking.objects.file import File


@dataclasses.dataclass
class Packet:
    id: bytes
    type: int
    offset: int
    total_size: int
    payload: bytes

    @staticmethod
    def format() -> str:
        return '<8sBII'

    def to_bytes(self) -> bytes:
        return struct.pack(self.format(), self.id, self.type, self.offset, self.total_size) + self.payload

    @staticmethod
    def from_bytes(data: bytes):
        header = data[:17]
        payload = data[17:]
        return Packet(*struct.unpack(Packet.format(), header), payload=payload)

    def __str__(self):
        return f"[{self.id.hex()}]"


# TODO REMOVE CHECKSUM IN PRODUCTION
class Header(Packet):
    def __init__(self, _id: bytes, total_size: int, path: str, checksum: bytes):
        super().__init__(_id, Header.default_type(), 0, total_size, checksum + path.encode("utf-8"))
        self.path = path
        self.checksum = checksum

    @classmethod
    def from_file(cls, file: File):
        return cls(file.id, len(file.bytes), file.path, file.checksum)

    @classmethod
    def from_packet(cls, packet: Packet):
        return cls(packet.id, packet.total_size, packet.payload[64:].decode("utf-8"), packet.payload[:64])

    @staticmethod
    def default_type():
        return 0

class Payload(Packet):
    def __init__(self, _id: bytes, offset: int, total_size: int, payload: bytes):
        super().__init__(_id, Payload.default_type(), offset, total_size, payload)

    @staticmethod
    def default_type():
        return 1

class End(Packet):
    def __init__(self):
        super().__init__(End.default_id(), End.default_type(), 0, 0, b'')

    @staticmethod
    def default_type():
        return 2

    @staticmethod
    def default_id():
        return b'\x00' * 8