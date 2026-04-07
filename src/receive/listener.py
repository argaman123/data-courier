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

    sock: socket.socket
    shm: shared_memory.SharedMemory
    buffer: memoryview

    def __init__(self, offset_queue: Queue[tuple[int, int]], shm_name: str):
        super().__init__(name=f"Listener", daemon=True)
        self.offset_queue = offset_queue
        self.shm_name = shm_name

    def _setup(self):
        # Must keep a handle so it doesn't get garbage collected
        self.shm = shared_memory.SharedMemory(name=self.shm_name)
        buffer = self.shm.buf
        if buffer is None:
            raise RuntimeError("Processor's shared memory buffer is missing")
        self.buffer = buffer
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.buffer_size)
        self.sock.bind((self.ip, self.port))

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        with logger.catch(message="Unexpected error occurred, shutting down..."):
            self._setup()
            logger.info(f"Listener is running on {self.sock.getsockname()}")

            offset = 0
            try:
                while True:
                    size = self.sock.recv_into(self.buffer[offset: offset + Packet.packet_size])
                    data = (offset, size)
                    try:
                        self.offset_queue.put_nowait(data)
                    except queue.Full:
                        logger.warning("Processor is too slow, waiting for it to catch up...")
                        self.offset_queue.put(data)

                    offset = (offset + size) % len(self.buffer)
                    if offset + Packet.packet_size >= len(self.buffer):
                        offset = 0
            except (ConnectionError, OSError) as e:
                logger.warning(f"An ignorable error occurred: {e}")
