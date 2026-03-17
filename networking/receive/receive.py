import logging
import socket

from config import settings
from networking.objects.packet import Packet
from networking.objects.partial_file import PartialFile
from networking.receive.disk import DiskThread

class Receiver:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, settings.buffer_size)
        self.sock.bind((settings.ip, settings.port))
        self.processing: dict[bytes, PartialFile] = {}
        self.disk_thread = DiskThread()

    # TODO TESTING ONLY
    def test_and_reset(self):
        for key, file in self.processing.copy().items():
            if not file.complete:
                progress = ""
                if self.processing[key].header is not None:
                    progress = f" ({len(self.processing[key].chunks)}/{self.processing[key].header.index})"
                logging.warning(f"Dropping {key}" + progress)
            self.processing.pop(key)

    def start(self):
        logging.info(f"Listening on {settings.ip}:{settings.port}")
        while True:
            packet = Packet.from_bytes(self.sock.recvfrom(2048)[0]) # bigger than 1413, and power of 2
            if packet.id not in self.processing:
                logging.info(f"Started processing {packet}")
                self.processing[packet.id] = PartialFile()
            if self.processing[packet.id].complete:
                continue
            done = self.processing[packet.id].process(packet)
            if self.processing[packet.id].complete:
                self.disk_thread.files.put(self.processing[packet.id])
            if done:
                self.test_and_reset()

if __name__ == "__main__":
    receiver = Receiver()
    receiver.start()