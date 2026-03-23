import json, math, socket, time
from pathlib import Path

from config import settings, logger
from objects.packet import Packet, End
from send.encoder import generate_chunks, calc_k_m
from objects.file import File
from send.pacer import Pacer


class Sender:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, settings.socket_buffer_size)
        self.pacer = Pacer()

    def send_packet(self, packet: Packet):
        self.sock.sendto(bytes(packet), (settings.ip, settings.port)) # maybe add packet size?
        self.pacer.wait_if_needed()


    def send_file(self, file: File):
        k, m = calc_k_m(len(file))
        chunks_amount = math.ceil(len(file) / (k * settings.payload_size))
        logger.info(f"Sending {file} ({chunks_amount} chunks of {k} packets) with {int((m-k)/m*100)}% redundancy, "
                    f"in {math.ceil(settings.packets_multiplier)} passes")
        
        for pass_num in range(math.ceil(settings.packets_multiplier)):
            size = 0
            start_time = time.perf_counter()
            for k, m, chunk_index, packet_index,  payload in generate_chunks(file, pass_num):
                size += len(payload)
                self.send_packet(Packet(0, file.id, len(file), k, m, chunk_index, packet_index,  payload))

            elapsed = time.perf_counter() - start_time
            if elapsed > 0:
                logger.info(f"Sent {file} (pass {pass_num + 1}/{math.ceil(settings.packets_multiplier)}) at "
                            f"{1 / (elapsed / size) / (1024 * 1024):.1f} MB/s")


if __name__ == "__main__":
    sender = Sender()
    global_time = time.perf_counter()
    total_bytes = 0
    input_folder = Path(settings.input_folder)
    checksums = {}
    for filepath in input_folder.rglob('*'):
        if filepath.is_file():
            _file = File(filepath)
            sender.send_file(_file)
            checksums[_file.path.name] = _file.checksum().hex()
            total_bytes += len(_file)
    with open("checksums", "w") as f:
        f.write(json.dumps(checksums))
    sender.send_packet(End())
    logger.success(f"Finished sending all files in {input_folder} at {(1/((time.perf_counter() - global_time)/total_bytes))/1_000_000:.1f} MB/s")
