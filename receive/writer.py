import os, threading, queue
from pathlib import Path

from config import settings, logger
from receive.partial_file import PartialFile

class Writer(threading.Thread):
    def __init__(self, _id: str):
        super().__init__()
        self.name = "Writer-" + _id
        self.daemon = True
        self.files: queue.Queue[PartialFile] = queue.Queue()

    def run(self):
        logger.info("Background disk writer thread started")
        while True:
            partial_file = self.files.get()
            (path, file_bytes) = partial_file.to_file()
            logger.info(f"Started saving {path}")
            with open(Path(settings.output_folder) / path, 'wb') as f:
                f.write(file_bytes)
            logger.success(f"Saved {path}")
            self.files.task_done()
