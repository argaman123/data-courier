import logging

from networking.objects.file import File
from networking.objects.packet import Packet


class PartialFile:
    def __init__(self):
        self.header: Packet | None = None
        self.chunks: dict[int, bytes] = {}
        self.complete: bool = False

    def to_file(self) -> File:
        return File(self.header.payload.decode('utf-8'),
                    b''.join(self.chunks[i] for i in range(len(self.chunks))), self.header.id)

    def process(self, packet: Packet) -> bool:
        if self.complete: return False

        match packet.type:
            case 0:
                self.header = packet
            case 1:
                self.chunks[packet.index] = packet.payload
            case 2: # TODO FOR TESTING
                return True

        if self.header is not None and self.header.index == len(self.chunks):
            self.complete = True
            logging.info(f"Finished receiving file [{packet.id.hex()}]")

        return False