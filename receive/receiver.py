import hashlib, socket
from pathlib import Path

from config import (settings, logger)
from objects.packet import Packet, End
from objects.partial_file import PartialFile
from receive.disk import DiskThread

class Receiver:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, settings.buffer_size)
        self.sock.bind((settings.ip, settings.port))
        self.processing: dict[bytes, PartialFile] = {}
        self.disk_thread = DiskThread()

    # TODO REMOVE TESTS IN PRODUCTION
    def test_and_reset(self):
        self.disk_thread.files.join()
        error = False
        logger.info("Verifying file integrity, and checking for missing packets")
        for key, partial_file in self.processing.copy().items():
            if key == End.default_id():
                pass
            elif partial_file.complete:
                actual_file = Path(Path(settings.output_folder)) / Path(partial_file.header.path)
                checksum = hashlib.blake2b(actual_file.read_bytes()).digest()
                if checksum != partial_file.header.checksum:
                    logger.error(f"File is malformed {partial_file.header.path} [{checksum.hex()} != {partial_file.header.checksum.hex()}]")
                    error = True
                actual_file.unlink()
            else:
                path = ""
                if partial_file.header is not None:
                    path = partial_file.header.path
                logger.error(f"Packets are missing {path} [{key.hex()}] {partial_file.data}")
                error = True
            self.processing.pop(key)
        if error:
            logger.error(f"Test failed")
        else:
            logger.success("All files arrived fully!")

    def start(self):
        logger.info(f"Listening on {settings.ip}:{settings.port}")
        while True:
            packet = Packet.from_bytes(self.sock.recvfrom(2048)[0]) # bigger than 1413, and power of 2
            if packet.id not in self.processing:
                logger.info(f"Started processing {packet}")
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