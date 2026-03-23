import copy
import hashlib
import json
from multiprocessing import shared_memory
from multiprocessing.queues import Queue

from pathlib import Path

from config import (settings, logger)
from objects.packet import Packet, End
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

    # TODO <editor-fold desc="REMOVE TEST IN PROD">
    def test_and_reset(self):
        self.writer.files.join()
        error = False
        logger.info("Verifying file integrity, and checking for missing packets")
        checksums: dict[str, str] = json.loads(Path("checksums").read_text())
        Path("checksums").unlink()
        for key, partial_file in self.processing.copy().items():
            if not partial_file.complete:
                logger.error(f"Packets are missing [{key.hex()}] {partial_file}")
                error = True
            self.processing.pop(key)
        for file in Path(settings.output_folder).rglob("*"):
            if file.is_file():
                checksum = hashlib.sha256(file.read_bytes()).digest().hex()
                if checksum != checksums[file.name]:
                    logger.error(f"File is malformed {file.name} [{checksum} != {checksums[file.name]}]")
                    error = True
                file.unlink()

        if error:
            logger.error(f"Test failed. Max index distance was {PartialFile.max_packet_index_distance}")
        else:
            logger.success(f"All files arrived fully! Max index distance was {PartialFile.max_packet_index_distance}")

    # TODO </editor-fold>

    def run(self):
        self.writer = Writer(self.id)
        self.writer.start()
        shm = shared_memory.SharedMemory(name=settings.shm_prefix + self.id)
        logger.info(f"Processor {self.id} is running")
        while True:
            offset, size = self.offset_queue.get()
            actual_bytes = shm.buf[offset:offset + size]
            packet = Packet.from_bytes(actual_bytes.tobytes())

            # TODO <editor-fold desc="REMOVE END IN PROD">
            if packet.type == End.default_type:
                self.test_and_reset()
                continue
            # TODO </editor-fold>

            if packet.file_id not in self.processing:
                logger.info(f"Started processing {packet}")
                self.processing[packet.file_id] = PartialFile()
            if not self.processing[packet.file_id].complete:
                if self.processing[packet.file_id].process(packet):
                    logger.info(f"Finished processing {self.processing[packet.file_id]}")
                    self.writer.files.put(copy.copy(self.processing[packet.file_id]))
                    self.processing[packet.file_id].free_memory()

            self.notify_monitor(size)