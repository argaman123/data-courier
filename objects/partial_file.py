from objects.file import File
from objects.packet import Packet, Header, End, Payload
from config import logger
from objects.partial_bytearray import PartialByteArray


class PartialFile:
    def __init__(self):
        self.header: Header | None = None
        self.data = PartialByteArray()
        self.complete: bool = False

    def to_file(self) -> File:
        return File(self.header.path, self.data.to_bytes(), self.header.id)

    def process(self, packet: Packet) -> bool:
        if self.complete: return False

        if packet.type == Header.default_type():
            self.header = Header.from_packet(packet)
        elif packet.type == Payload.default_type():
            self.data.insert(packet)
        elif packet.type == End.default_type():
            return True

        if self.header is not None and self.data.is_complete():
            self.complete = True
            logger.info(f"Finished receiving {self}")

        return False

    def __str__(self):
        return f"[{self.header.id.hex()}]"