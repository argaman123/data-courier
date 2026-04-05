import time
from threading import Thread
from pathlib import Path

from src.common.config import settings, logger
from src.common.sized_queue import MemoryBoundedQueue
from src.receive.partial_file import PartialFile
from src.receive.rabbitmq import RabbitMQ


class Writer(Thread):
    buffer_limit = settings.writer.buffer_limit
    output_folder = settings.output_folder

    def __init__(self, rabbitmq: RabbitMQ):
        super().__init__(name="Writer", daemon=True)
        self.rabbitmq = rabbitmq
        self.files: MemoryBoundedQueue[PartialFile] = MemoryBoundedQueue(self.buffer_limit)
        self.output = Path(self.output_folder)

    def run(self):
        logger.info("Background disk writer started")
        while True:
            partial_file = self.files.get()
            (path, file_bytes) = partial_file.to_file()
            logger.info(f"Started saving {path}")
            file = self.output / path
            folder = file.parent
            folder.mkdir(exist_ok=True)
            with open(file, 'wb') as f:
                f.write(file_bytes)
            logger.success(f"Saved {path}")
            del partial_file, file_bytes
            self.rabbitmq.notify(folder.name, path)
