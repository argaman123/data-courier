from __future__ import annotations

import math, socket, time
import re
import signal
from multiprocessing import Process
from multiprocessing.queues import Queue
import multiprocessing.sharedctypes as mp_types
from pathlib import Path

import zfec

from src.common.config import settings, logger
from src.common.packet import Packet
from src.send.encoder import generate_chunks, calc_k_m
from src.send.file import File
from src.send.pacer import Pacer

def to_camel_case(text):
    s = re.sub(r"([_\-])+", " ", text)
    s = s.title()
    s = s.replace(" ", "")
    return s


class Sender(Process):
    temp_folder = settings.temp_folder
    buffer_size = settings.socket.get('buffer_size', 256_000_000)
    ip, port = settings.socket.ip, settings.socket.port

    sock: socket.socket
    temp_path: Path

    def __init__(self, folder: str, queue: Queue[str], active_senders: 'mp_types.Synchronized'):
        super().__init__(name=f"{to_camel_case(folder)}Sender", daemon=True)
        self.folder = folder
        self.queue = queue
        self.active_senders = active_senders


    def _setup(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.buffer_size)
        self.sock.connect((self.ip, self.port))
        self.temp_path = Path(self.temp_folder)

    def send_file(self, file: File, sock: socket.socket):
        pacer = Pacer(self.active_senders)
        k, m = calc_k_m(len(file))
        passes = math.ceil(m/k)
        chunks_amount = math.ceil(len(file) / (k * Packet.payload_size))
        logger.info(f"Sending {file} ({chunks_amount} chunks of {k} packets) with {int((m-k)/m*100)}% redundancy, "
                    f"in {passes} passes")
        for pass_num in range(passes):
            size = 0
            start_time = time.perf_counter()
            for packet in generate_chunks(file, pass_num):
                size += len(packet)
                sock.send(bytes(packet))
                pacer.wait_if_needed(len(packet))
            elapsed = time.perf_counter() - start_time
            if elapsed > 0:
                logger.info(f"Sent {file} (pass {pass_num + 1}/{passes}) at "
                            f"{1 / (elapsed / size) / (1024 * 1024):.1f} MB/s")

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        with logger.catch(message="Unexpected error occurred, shutting down..."):
            self._setup()
            logger.info(f"Sender for {self.folder} is running")

            while True:
                file = self.queue.get()
                path = self.temp_path / file

                with self.active_senders.get_lock():
                    self.active_senders.value += 1

                try:
                    self.send_file(File(file, self.temp_path), self.sock)
                    path.unlink(missing_ok=True)
                except (OSError, ValueError, zfec.Error) as e:
                    if not path.exists():
                        logger.warning(f"Dropping {file} since it disappeared from {self.temp_path}")
                    else:
                        logger.warning(f"Error occurred while sending {file}. Re-queueing: {e}")
                        self.queue.put(file)
                        time.sleep(1)
                finally:
                    with self.active_senders.get_lock():
                        self.active_senders.value -= 1
