import logging
import socket
import time

from config import settings
from networking.objects.file import File
from networking.objects.packet import Packet
from networking.send.pacing import Pacer


class Sender:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, settings.buffer_size)
        self.pacer = Pacer()

    def send_packet(self, packet: Packet, immediate=False):
        self.sock.sendto(packet.to_bytes(), (settings.ip, settings.port)) # maybe add packet size?
        if not immediate: self.pacer.wait_if_needed()

    def send_file(self, file: File):
        chunks = [file.bytes[i:i + settings.chunk_size] for i in range(0, len(file.bytes), settings.chunk_size)]
        logging.info(f"Sending {file.path} [{file.id.hex()}] ({len(chunks)} chunks)")
        for pass_num in range(settings.passes):
            start_time = time.perf_counter()
            self.send_packet(Packet(file.id, 0, len(chunks), file.path.encode('utf-8')))
            for index, payload in enumerate(chunks):
                self.send_packet(Packet(file.id, 1, index, payload))
            logging.info(f"Sent {file.path} {pass_num + 1}/{settings.passes} at {(1/((time.perf_counter() - start_time)/len(file.bytes)))/1_000_000:.1f}MB/s")


if __name__ == "__main__":
    sender = Sender()
    global_time = time.perf_counter()
    total_bytes = 0
    from pathlib import Path
    input_folder = Path(settings.input_folder)
    for filepath in input_folder.rglob('*'):
        if filepath.is_file():
            path = filepath.relative_to(input_folder)
            file_bytes = filepath.read_bytes()
            total_bytes += len(file_bytes)
            sender.send_file(File(str(path), file_bytes))
    logging.info(f"Finished sending all files in {input_folder} at {(1/((time.perf_counter() - global_time)/total_bytes))/1_000_000:.1f}MB/s, sending save signal")
    sender.send_packet(Packet(b'', 2, 0, b'')) # TODO FOR TESTING