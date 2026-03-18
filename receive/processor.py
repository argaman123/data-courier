import hashlib, multiprocessing
import queue
import time
from multiprocessing import shared_memory
from multiprocessing.queues import Queue

from pathlib import Path

from config import (settings, logger)
from objects.packet import Packet, End
from objects.partial_file import PartialFile
from receive.writer import Writer
from send.pacer import Pacer


class Processor(multiprocessing.Process):
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
                checksum = hashlib.blake2b(actual_file.read_bytes()).digest()
                if checksum != partial_file.header.checksum:
                    logger.error(f"File is malformed {partial_file.header.path} [{checksum.hex()} != {partial_file.header.checksum.hex()}]")
                    error = True
                actual_file.unlink()
            else:
                path = ""
                if partial_file.header is not None:
                    path = partial_file.header.path
                logger.error(f"Packets are missing {path} [{key.hex()}] {partial_file.data}")
                error = True
            self.processing.pop(key)
        if error:
            logger.error(f"Test failed")
        else:
            logger.success("All files arrived fully!")

    def run(self):
        self.writer = Writer(self.id)
        self.writer.start()
        shm = shared_memory.SharedMemory(name=settings.shm_prefix + self.id)
        logger.info(f"Processor {self.id} is running")
        while True:
            offset, size = self.offset_queue.get()
            actual_bytes = shm.buf[offset:offset + size]
            packet = Packet.from_bytes(actual_bytes.tobytes())
            if packet.id not in self.processing:
                logger.info(f"Started processing {packet}")
                self.processing[packet.id] = PartialFile()
            if self.processing[packet.id].complete:
                continue
            done = self.processing[packet.id].process(packet)
            if self.processing[packet.id].complete:
                self.writer.files.put(self.processing[packet.id])
            if done:
                self.test_and_reset()