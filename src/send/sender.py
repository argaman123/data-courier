import math, socket, time
import re
import signal
from multiprocessing import Process
from multiprocessing.queues import Queue
import multiprocessing.sharedctypes as mp_types
from pathlib import Path

from src.config import settings, logger
from src.objects.packet import Packet
from src.send.encoder import generate_chunks, calc_k_m
from src.objects.file import File
from src.send.pacer import Pacer


def to_camel_case(text):
    s = re.sub(r"([_\-])+", " ", text)
    s = s.title()
    s = s.replace(" ", "")
    return s

class Sender(Process):
    def __init__(self, folder: str, queue: Queue[str], active_senders: 'mp_types.Synchronized'):
        super().__init__(name=f"{to_camel_case(folder)}Sender", daemon=True)
        self.socket: socket.socket | None = None
        self.folder = folder
        self.queue = queue
        self.active_senders = active_senders
        self.pacer = Pacer(active_senders)

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, settings.socket_buffer_size)
        logger.info(f"Sender for {self.folder} is running")
        folder = Path(settings.temp_folder)
        while True:
            file = self.queue.get()

            with self.active_senders.get_lock():
                self.active_senders.value += 1

            path = folder / file
            self.send_file(File(file, folder))
            path.unlink()

            with self.active_senders.get_lock():
                self.active_senders.value -= 1

    def send_packet(self, packet: Packet):
        self.socket.sendto(bytes(packet), (settings.ip, settings.port))
        self.pacer.wait_if_needed()

    def send_file(self, file: File):
        k, m = calc_k_m(len(file))
        chunks_amount = math.ceil(len(file) / (k * settings.payload_size))
        logger.info(f"Sending {file} ({chunks_amount} chunks of {k} packets) with {int((m-k)/m*100)}% redundancy, "
                    f"in {math.ceil(settings.packets_multiplier)} passes")
        for pass_num in range(math.ceil(settings.packets_multiplier)):
            size = 0
            start_time = time.perf_counter()
            for packet in generate_chunks(file, pass_num):
                size += len(packet)
                self.send_packet(packet)
            elapsed = time.perf_counter() - start_time
            if elapsed > 0:
                logger.info(f"Sent {file} (pass {pass_num + 1}/{math.ceil(settings.packets_multiplier)}) at "
                            f"{1 / (elapsed / size) / (1024 * 1024):.1f} MB/s")
