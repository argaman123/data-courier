import struct
from threading import Thread
from pathlib import Path

from src.common.config import settings, logger
from src.common.sized_queue import SizedQueue
from src.receive.partial_file import PartialFile
from src.receive.rabbitmq import RabbitMQ


class Writer(Thread):
    buffer_limit = settings.writer.buffer_limit
    output_folder = settings.output_folder

    def __init__(self, rabbitmq: RabbitMQ | None):
        super().__init__(name="Writer", daemon=True)
        self.rabbitmq = rabbitmq
        self.files: SizedQueue[PartialFile] = SizedQueue(self.buffer_limit)
        self.output = Path(self.output_folder)

    def run(self):
        with logger.catch(message="Unexpected error occurred, shutting down..."):
            logger.info("Background disk writer started")
            while True:
                partial_file = self.files.get()

                try:
                    (path, file_bytes) = partial_file.to_file()
                except (struct.error, UnicodeError) as e:
                    logger.warning(f"Received a corrupted file {partial_file}: {e}")
                    del partial_file
                    continue

                logger.info(f"Started saving {path}")
                file = self.output / path
                folder = file.parent

                try:
                    folder.mkdir(exist_ok=True)
                    with open(file, 'wb') as f:
                        f.write(file_bytes)
                except OSError as e:
                    logger.error(f"Failed to write {file}: {e}")
                    del partial_file, file_bytes
                    continue

                logger.success(f"Saved {path}")
                del partial_file, file_bytes
                if self.rabbitmq:
                    self.rabbitmq.notify(folder.name, path)
