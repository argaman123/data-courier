import logging
import socket
from pathlib import Path

from config import settings
from networking.objects.packet import Packet
from networking.objects.partial_file import PartialFile

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
                file.save(str('..' / Path(settings.output_folder)))
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