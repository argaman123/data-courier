import logging
import socket
import time

from config import settings
from networking.objects import File, Packet

def create_pacer():
    target_batch_time = (settings.batch_size * settings.chunk_size) / settings.network_speed
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

    def send_packet(self, packet: Packet):
        self.sock.sendto(packet.to_bytes(), (settings.ip, settings.port)) # maybe add packet size?

    def send_file(self, file: File):
        chunks = [file.bytes[i:i + settings.chunk_size] for i in range(0, len(file.bytes), settings.chunk_size)]
        logging.info(f"Sending {file.path} [{file.id.hex()}] ({len(chunks)} chunks)")
        self.send_packet(Packet(file.id, 0, len(chunks), file.path.encode('utf-8')))
        pacer = create_pacer()
        for pass_num in range(settings.passes):
            for index, payload in enumerate(chunks):
                self.send_packet(Packet(file.id, 1, index, payload))
                next(pacer)
            logging.info(f"Sent {file.path} {pass_num + 1}/{settings.passes}")


if __name__ == "__main__":
    sender = Sender()

    from pathlib import Path
    input_folder = Path(settings.input_folder)
    for filepath in input_folder.rglob('*'):
        if filepath.is_file():
            path = filepath.relative_to(input_folder)
            sender.send_file(File(str(path), filepath.read_bytes()))
    logging.info(f"Finished sending all files in {input_folder}, sending save signal")
    sender.send_packet(Packet(bytes(), 2, 0, bytes()))