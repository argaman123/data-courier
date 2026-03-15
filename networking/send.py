import logging
import socket
import time

from config import settings
from networking.objects import File, Packet

def create_pacer():
    target_batch_time = (settings.batch_size * settings.chunk_size) / settings.network_speed
    logging.info(f"Pacer initialized {target_batch_time:.3f}s / {settings.batch_size} packets")
    packets_sent = 0
    start_time = time.perf_counter()

    while True:
        yield
        packets_sent += 1
        if packets_sent == settings.batch_size:
            elapsed_time = time.perf_counter() - start_time
            if elapsed_time < target_batch_time:
                time.sleep(target_batch_time - elapsed_time)
            packets_sent = 0
            start_time = time.perf_counter()

class Sender:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, settings.buffer_size)
        self.pacer = create_pacer()

    def send_packet(self, packet: Packet):
        self.sock.sendto(packet.to_bytes(), (settings.ip, settings.port)) # maybe add packet size?

    def send_file(self, file: File):
        chunks = [file.bytes[i:i + settings.chunk_size] for i in range(0, len(file.bytes), settings.chunk_size)]
        logging.info(f"Sending {file.path} [{file.id.hex()}] ({len(chunks)} chunks)")
        self.send_packet(Packet(file.id, 0, len(chunks), file.path.encode('utf-8')))
        for pass_num in range(settings.passes):
            start_time = time.perf_counter()
            for index, payload in enumerate(chunks):
                self.send_packet(Packet(file.id, 1, index, payload))
                next(self.pacer)
            logging.info(f"Sent {file.path} {pass_num + 1}/{settings.passes} at {(1/((time.perf_counter() - start_time)/len(file.bytes)))/1_000_000:.1f}MB/s")


if __name__ == "__main__":
    sender = Sender()
    start_time = time.perf_counter()
    total_bytes = 0
    from pathlib import Path
    input_folder = Path(settings.input_folder)
    for filepath in input_folder.rglob('*'):
        if filepath.is_file():
            path = filepath.relative_to(input_folder)
            file_bytes = filepath.read_bytes()
            total_bytes += len(file_bytes)
            sender.send_file(File(str(path), file_bytes))
    logging.info(f"Finished sending all files in {input_folder} at {(1/((time.perf_counter() - start_time)/total_bytes))/1_000_000:.1f}MB/s, sending save signal")
    sender.send_packet(Packet(b'', 2, 0, b'')) # TODO FOR TESTING