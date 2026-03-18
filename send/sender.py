import socket
import time

from config import settings, logger
from objects.file import File
from objects.packet import Packet, Payload, Header, End
from send.pacer import Pacer


class Sender:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, settings.socket_buffer_size)
        self.pacer = Pacer()

    def send_packet(self, packet: Packet, immediate=False):
        self.sock.sendto(packet.to_bytes(), (settings.ip, settings.port)) # maybe add packet size?
        if not immediate: self.pacer.wait_if_needed()

    def send_file(self, file: File):
        raw_bytes = memoryview(file.bytes)
        chunks = [(i, raw_bytes[i:i + settings.payload_size]) for i in range(0, len(raw_bytes), settings.payload_size)]
        logger.info(f"Sending {file} ({len(chunks)} chunks)")
        for pass_num in range(settings.passes):
            start_time = time.perf_counter()
            self.send_packet(Header.from_file(file))
            for offset, payload in chunks:
                self.send_packet(Payload(file.id, offset, len(raw_bytes), payload.tobytes()))
            logger.info(f"Sent {file} (pass {pass_num + 1}/{settings.passes}) at {(1/((time.perf_counter() - start_time)/len(raw_bytes)))/1_000_000:.1f}MB/s")


if __name__ == "__main__":
    sender = Sender()
    global_time = time.perf_counter()
    total_bytes = 0
    from pathlib import Path
    input_folder = Path(settings.input_folder)
    for filepath in input_folder.rglob('*'):
        if filepath.is_file():
            path = filepath.relative_to(input_folder)
            logger.info(f"Reading {path}")
            file_bytes = filepath.read_bytes()
            total_bytes += len(file_bytes)
            sender.send_file(File(str(path), file_bytes))
    logger.success(f"Finished sending all files in {input_folder} at {(1/((time.perf_counter() - global_time)/total_bytes))/1_000_000:.1f}MB/s")
    sender.send_packet(End())