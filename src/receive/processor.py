from __future__ import annotations

import copy
import signal
from multiprocessing import shared_memory, Process
from multiprocessing.queues import Queue

from src.common.config import (settings, logger)
from src.common.packet import Packet
from src.common.sized_queue import SizedQueue
from src.receive.cleaner import Cleaner
from src.receive.partial_file import PartialFile
from src.receive.writer import Writer
from src.receive.rabbitmq import RabbitMQ


class Processor(Process):
    def __init__(self, offset_queue: Queue[tuple[int, int]], shm_name: str):
        super().__init__(name=f"Processor", daemon=True)
        self.offset_queue = offset_queue
        self.shm = shared_memory.SharedMemory(name=shm_name)
        self.processing: dict[bytes, PartialFile] = {}

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        rabbitmq = RabbitMQ()
        rabbitmq.start()
        writer = Writer(rabbitmq)
        writer.start()
        cleaner = Cleaner(self.processing)
        cleaner.start()

        logger.info(f"Processor is running")
        while True:
            offset, size = self.offset_queue.get()
            actual_bytes = self.shm.buf[offset:offset + size]
            packet = Packet.from_bytes(actual_bytes.tobytes())
            cleaner.register(packet.file_id)
            with cleaner.lock:
                if packet.file_id not in self.processing:
                    logger.info(f"Started processing {packet}")
                    self.processing[packet.file_id] = PartialFile()
                current_file = self.processing[packet.file_id]
                is_complete = False
                if not current_file.complete:
                    is_complete = current_file.process(packet)
            if is_complete:
                logger.info(f"Finished processing {current_file}")
                current_file_copy = copy.copy(current_file)
                try:
                    writer.files.put_nowait(current_file_copy, current_file_copy.file_size)
                except SizedQueue.Full:
                    logger.warning("Writer is too slow, waiting for it to catch up...")
                    writer.files.put(current_file_copy, current_file_copy.file_size)
                current_file.free_memory()