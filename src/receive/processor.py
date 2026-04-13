from __future__ import annotations

import copy
import signal
import queue
import struct
from multiprocessing import shared_memory, Process
from multiprocessing.queues import Queue
from threading import Thread

from src.common.config import logger
from src.common.packet import Packet
from src.common.sized_queue import SizedQueue
from src.receive.cleaner import Cleaner
from src.receive.partial_file import PartialFile
from src.receive.writer import Writer
from src.receive.rabbitmq import RabbitMQ


class Processor(Process):
    shm: shared_memory.SharedMemory
    buffer: memoryview
    processing: dict[bytes, PartialFile]
    rabbitmq: RabbitMQ
    writer: Writer
    cleaner: Cleaner
    threads: list[Thread]

    def __init__(self, offset_queue: Queue[tuple[int, int]], shm_name: str):
        super().__init__(name=f"Processor", daemon=True)
        self.offset_queue = offset_queue
        self.shm_name = shm_name

    def _setup(self):
        # Must keep a handle so it doesn't get garbage collected
        self.shm = shared_memory.SharedMemory(name=self.shm_name)
        buffer = self.shm.buf
        if buffer is None:
            raise RuntimeError("Processor's shared memory buffer is missing")
        self.buffer = buffer
        self.processing = {}
        self.rabbitmq = RabbitMQ()
        self.writer = Writer(self.rabbitmq if self.rabbitmq.enabled else None)
        self.cleaner = Cleaner(self.processing)

        self.threads: list[Thread] = [self.writer, self.cleaner]
        if self.rabbitmq.enabled:
            self.threads.append(self.rabbitmq)

        for thread in self.threads:
            thread.start()

    def _threads_healthcheck(self):
        for thread in self.threads:
            if not thread.is_alive():
                logger.critical(f"{thread.name} is not running, shutting down...")
                return False
        return True

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        with logger.catch(message="Unexpected error occurred, shutting down..."):
            self._setup()
            logger.info(f"Processor is running")

            while True:
                try:
                    offset, size = self.offset_queue.get(timeout=1.0)
                except queue.Empty:
                    # Checking for dying threads only when the Processor is not under heavy load
                    if not self._threads_healthcheck():
                        return
                    continue

                actual_bytes = self.buffer[offset:offset + size]
                try:
                    packet = Packet.from_bytes(actual_bytes.tobytes())
                except struct.error:
                    continue

                self.cleaner.register(packet.file_id)
                with self.cleaner.lock:
                    if packet.file_id not in self.processing:
                        logger.info(f"Started processing {packet}")
                        self.processing[packet.file_id] = PartialFile(packet)
                    current_file = self.processing[packet.file_id]
                    is_complete = False
                    if not current_file.complete:
                        is_complete = current_file.process(packet)
                if is_complete:
                    logger.info(f"Finished processing {current_file}")
                    current_file_copy = copy.copy(current_file)
                    try:
                        self.writer.files.put_nowait(current_file_copy)
                    except SizedQueue.Full:
                        logger.warning("Writer is too slow, waiting for it to catch up...")
                        self.writer.files.put(current_file_copy)
                    current_file.free_memory()