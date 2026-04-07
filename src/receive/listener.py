from __future__ import annotations

import queue
import signal
import socket
from multiprocessing import shared_memory, Process
from multiprocessing.queues import Queue
from src.common.config import settings, logger
from src.common.packet import Packet


class Listener(Process):
    buffer_size = settings.socket.get('buffer_size', 256_000_000)
    ip, port = settings.socket.ip, settings.socket.port

    def __init__(self, offset_queue: Queue[tuple[int, int]], shm_name: str):
        super().__init__(name=f"Listener", daemon=True)
        self.offset_queue = offset_queue
        self.shm_name = shm_name

    def initialize_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.buffer_size)
        sock.bind((self.ip, self.port))
        return sock

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        buffer = shared_memory.SharedMemory(name=self.shm_name).buf
        if buffer is None:
            raise RuntimeError("Processor's shared memory buffer is missing")
        sock = self.initialize_socket()
        logger.info(f"Listener is running on {sock.getsockname()}")

        offset = 0
        while True:
            size = sock.recv_into(buffer[offset: offset + Packet.packet_size])
            data = (offset, size)
            try:
                self.offset_queue.put_nowait(data)
            except queue.Full:
                logger.warning("Processor is too slow, waiting for it to catch up...")
                self.offset_queue.put(data)

            offset = (offset + size) % len(buffer)
            if offset + Packet.packet_size >= len(buffer):
                offset = 0
