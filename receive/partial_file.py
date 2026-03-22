from objects.file import File
from objects.packet import Packet, Header, End, Payload
from config import logger
from receive.decoder import Decoder


class PartialFile:
    def __init__(self):
        self.header: Header | None = None
        self.decoder = Decoder()
        self.complete: bool = False

    def free_memory(self):
        # TODO RETURN IN PRODUCTION
        # self.header = None
        self.decoder = None

    def to_file(self) -> File:
        return File(self.header.path, self.decoder.to_bytes(), self.header.file_id)

    def process(self, packet: Packet) -> bool:
        if self.complete: return False

        if packet.type == Header.default_type:
            self.header = Header.from_packet(packet)
        elif packet.type == Payload.default_type:
            self.decoder.process(packet)
        elif packet.type == End.default_type:
            return True

        if self.header is not None and self.decoder.is_complete():
            self.complete = True
            logger.info(f"Finished processing {self}")

        return False

    def __str__(self):
        return f"[{self.header.file_id.hex()}]"