import os, threading, queue
from pathlib import Path

from config import settings, logger
from objects.partial_file import PartialFile

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
            file = partial_file.to_file()
            logger.info(f"Started saving {file}")
            with open(os.path.join(str(Path(settings.output_folder)), file.path), 'wb') as f:
                f.write(file.bytes)
            logger.success(f"Saved {file}")
            self.files.task_done()
