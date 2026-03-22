import copy
import hashlib
from multiprocessing import shared_memory
from multiprocessing.queues import Queue

from pathlib import Path

from config import (settings, logger)
from objects.packet import Packet, End
from receive.decoder import Decoder
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

    # TODO REMOVE TESTS IN PRODUCTION
    def test_and_reset(self):
        self.writer.files.join()
        error = False
        logger.info("Verifying file integrity, and checking for missing packets")
        for key, partial_file in self.processing.copy().items():
            if key == End.default_id:
                pass
            elif partial_file.complete:
                actual_file = Path(Path(settings.output_folder)) / Path(partial_file.header.path)
                checksum = hashlib.sha256(actual_file.read_bytes()).digest()
                if checksum != partial_file.header.checksum:
                    logger.error(f"File is malformed {partial_file.header.path} [{checksum.hex()} != {partial_file.header.checksum.hex()}]")
                    error = True
                actual_file.unlink()
            else:
                path = ""
                if partial_file.header is not None:
                    path = partial_file.header.path
                logger.error(f"Packets are missing {path} [{key.hex()}] {partial_file.decoder}")
                error = True
            self.processing.pop(key)
        if error:
            logger.error(f"Test failed. Max index distance was {Decoder.max_packet_index_distance}")
        else:
            logger.success(f"All files arrived fully! Max index distance was {Decoder.max_packet_index_distance}")

    def run(self):
        self.writer = Writer(self.id)
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
                done = self.processing[packet.file_id].process(packet)
                if self.processing[packet.file_id].complete:
                    self.writer.files.put(copy.copy(self.processing[packet.file_id]))
                    self.processing[packet.file_id].free_memory()
                if done:
                    self.test_and_reset()

            self.notify_monitor(size)