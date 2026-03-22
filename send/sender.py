import math
import socket
import time
import zfec

from config import settings, logger
from objects.file import File
from objects.packet import Packet, Payload, Header, End
from send.pacer import Pacer


class Sender:
    minimum_packets = 256 // settings.passes
    total_packets = minimum_packets * settings.passes
    chunk_size = minimum_packets * settings.payload_size
    encoder = zfec.Encoder(minimum_packets, total_packets)

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, settings.socket_buffer_size)
        self.pacer = Pacer()

    def send_packet(self, packet: Packet, immediate=False):
        self.sock.sendto(bytes(packet), (settings.ip, settings.port)) # maybe add packet size?
        if not immediate: self.pacer.wait_if_needed()

    def _chunked_data(self, raw_bytes: memoryview, window_size=100):
        window: list[tuple[int, list]] = []
        for chunk_index, offset in enumerate(range(0, len(raw_bytes), self.chunk_size)):
            chunk = raw_bytes[offset:offset + self.chunk_size]

            if len(chunk) < self.chunk_size:
                chunk = bytes(chunk) + b'\x00' * (self.chunk_size - len(chunk))

            payloads = [chunk[i:i + settings.payload_size] for i in range(0, self.chunk_size, settings.payload_size)]
            # noinspection PyArgumentList
            window.append((chunk_index, self.encoder.encode(payloads)))
            
            if len(window) >= window_size:
                yield window
                window = []
        if window:
            yield window

    def send_file(self, file: File):
        header = Header.from_file(file)
        raw_bytes = memoryview(file.bytes)
        
        total_chunks = math.ceil(len(raw_bytes) / self.chunk_size)
        logger.info(f"Sending {file} ({total_chunks} chunks)")
        
        for pass_num in range(settings.passes):
            size = 0
            start_time = time.perf_counter()

            self.send_packet(header)
            starting_packet_index = pass_num * self.minimum_packets
            for window in self._chunked_data(raw_bytes, window_size=100):
                for packet_index in range(starting_packet_index, starting_packet_index + self.minimum_packets):
                    for chunk_index, payloads in window:
                        size += len(payloads[packet_index])
                        self.send_packet(Payload(file.id, chunk_index, packet_index, len(raw_bytes), payloads[packet_index]))

            elapsed = time.perf_counter() - start_time
            if elapsed > 0:
                logger.info(f"Sent {file} (pass {pass_num + 1}/{settings.passes}) at "
                            f"{1 / (elapsed / len(raw_bytes)) / (1024 * 1024):.1f} MB/s")


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
    logger.success(f"Finished sending all files in {input_folder} at {(1/((time.perf_counter() - global_time)/total_bytes))/1_000_000:.1f} MB/s")
    sender.send_packet(End())