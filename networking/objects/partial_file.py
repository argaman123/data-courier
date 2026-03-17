import logging
from typing import cast

from networking.objects.file import File
from networking.objects.packet import Packet, Header, End, Payload


class PartialFile:
    def __init__(self):
        self.header: Header | None = None
        self.chunks: dict[int, bytes] = {}
        self.complete: bool = False

    def to_file(self) -> File:
        return File(self.header.payload.decode('utf-8'),
                    b''.join(self.chunks[i] for i in range(len(self.chunks))), self.header.id)

    def process(self, packet: Packet) -> bool:
        if self.complete: return False

        if packet.type == Header.default_type():
            self.header = cast(Header, packet)
        elif packet.type == Payload.default_type():
            self.chunks[packet.index] = packet.payload
        elif packet.type == End.default_type():
            return True

        if self.header is not None and self.header.index == len(self.chunks):
            self.complete = True
            logging.info(f"Finished receiving {self}")

        return False

    def __str__(self):
        return f"[{self.header.id.hex()}]"