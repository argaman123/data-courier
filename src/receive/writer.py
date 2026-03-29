import threading, queue
from pathlib import Path

from src.config import settings, logger
from src.receive.partial_file import PartialFile


class Writer(threading.Thread):
    def __init__(self):
        super().__init__(name="Writer", daemon=True)
        self.files: queue.Queue[PartialFile] = queue.Queue(maxsize=settings.file_queue_size)

    def run(self):
        logger.info("Background disk writer thread started")
        while True:
            partial_file = self.files.get()
            (path, file_bytes) = partial_file.to_file()
            logger.info(f"Started saving {path}")
            file = Path(settings.output_folder) / path
            file.parent.mkdir(exist_ok=True)
            with open(file, 'wb') as f:
                f.write(file_bytes)
            logger.success(f"Saved {path}")
            self.files.task_done()
            del partial_file, file_bytes
