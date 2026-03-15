import logging
import socket

from config import settings
from networking.objects import Packet, File


class PartialFile:
    def __init__(self):
        self.header: Packet | None = None
        self.chunks: dict[int, Packet] = {}
        self.complete: bool = False

    def to_file(self) -> File:
        return File(self.header.payload.decode('utf-8'),
                    b''.join(self.chunks[i].payload for i in range(len(self.chunks))), self.header.id)

    def process(self, packet: Packet) -> bool:
        if self.complete: return False

        match packet.type:
            case 0:
                self.header = packet
            case 1:
                self.chunks[packet.index] = packet
            case 2: # TODO FOR TESTING
                return True

        if self.header is not None and self.header.index == len(self.chunks):
            self.complete = True
            logging.info(f"Finished receiving file [{packet.id.hex()}]")

        return False


class Receiver:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, settings.buffer_size)
        self.sock.bind((settings.ip, settings.port))
        self.processing: dict[bytes, PartialFile] = {}

    def save_files(self):
        logging.info(f"Saving all completed files")
        for file_id, partial_file in self.processing.copy().items():
            if partial_file.complete:
                file = partial_file.to_file()
                file.save(settings.output_folder)
                logging.info(f"Saved file {file.path}")
            else:
                progress = ""
                if partial_file.header is not None:
                    progress = f" ({len(partial_file.chunks)}/{partial_file.header.index})"
                logging.warning(f"Skipping file [{file_id.hex()}]" + progress)
            self.processing.pop(file_id)

    def start(self):
        logging.info(f"Listening on {settings.ip}:{settings.port}")

        while True:
            packet = Packet.from_bytes(self.sock.recvfrom(2048)[0]) # bigger than 1413, and power of 2
            if packet.id not in self.processing:
                logging.info(f"Started processing file [{packet.id.hex()}]")
                self.processing[packet.id] = PartialFile()

            if self.processing[packet.id].process(packet):
                self.save_files()

if __name__ == "__main__":
    receiver = Receiver()
    receiver.start()