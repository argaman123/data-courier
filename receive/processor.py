import copy
from multiprocessing import shared_memory
from multiprocessing.queues import Queue

from config import (settings, logger)
from objects.packet import Packet
from receive.partial_file import PartialFile
from receive.monitor import MonitoredProcess
from receive.writer import Writer


class Processor(MonitoredProcess):
    def __init__(self, _id: str, offset_queue: Queue[tuple[int, int]]):
        super().__init__(name=f"Processor-{_id}", daemon=True)
        self.id = _id
        self.offset_queue = offset_queue
        self.processing: dict[bytes, PartialFile] = {}
        self.writer: Writer | None = None

    def run(self):
        self.writer = Writer(self.id, self)
        self.writer.start()
        shm = shared_memory.SharedMemory(name=settings.shm_prefix + self.id)
        logger.info(f"Processor {self.id} is running")
        while True:
            offset, size = self.offset_queue.get()
            actual_bytes = shm.buf[offset:offset + size]
            packet = Packet.from_bytes(actual_bytes.tobytes())
            if packet.file_id not in self.processing:
                logger.info(f"Started processing {packet}")
                self.processing[packet.file_id] = PartialFile()
            if not self.processing[packet.file_id].complete:
                if self.processing[packet.file_id].process(packet):
                    logger.info(f"Finished processing {self.processing[packet.file_id]}")
                    self.writer.files.put(copy.copy(self.processing[packet.file_id]))
                    self.processing[packet.file_id].free_memory()

            self.notify_monitor(size)