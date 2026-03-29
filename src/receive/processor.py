import copy
from multiprocessing import shared_memory
from multiprocessing.queues import Queue

from src.config import (settings, logger)
from src.objects.packet import Packet
from src.receive.partial_file import PartialFile
from src.receive.monitor import MonitoredProcess
from src.receive.writer import Writer


class Processor(MonitoredProcess):
    def __init__(self, offset_queue: Queue[tuple[int, int]]):
        super().__init__(name=f"Processor", daemon=True)
        self.offset_queue = offset_queue
        self.processing: dict[bytes, PartialFile] = {}
        self.writer: Writer | None = None

    def run(self):
        super().run()
        self.writer = Writer()
        self.writer.start()
        shm = shared_memory.SharedMemory(name=settings.shm_name)
        logger.info(f"Processor is running")
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