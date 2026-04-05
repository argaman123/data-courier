import queue
from threading import Thread
from pathlib import Path

from src.common.config import settings, logger
from src.receive.partial_file import PartialFile
from src.send.rabbitmq import RabbitMQ


class Writer(Thread):
    def __init__(self, rabbitmq: RabbitMQ):
        super().__init__(name="Writer", daemon=True)
        self.rabbitmq = rabbitmq
        self.files: queue.Queue[PartialFile] = queue.Queue(maxsize=settings.file_queue_size)

    def run(self):
        logger.info("Background disk writer started")
        while True:
            partial_file = self.files.get()
            (path, file_bytes) = partial_file.to_file()
            logger.info(f"Started saving {path}")
            file = Path(settings.output_folder) / path
            folder = file.parent
            folder.mkdir(exist_ok=True)
            with open(file, 'wb') as f:
                f.write(file_bytes)
            logger.success(f"Saved {path}")
            del partial_file, file_bytes
            self.rabbitmq.notify(folder.name, path)
