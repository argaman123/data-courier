import os, threading, queue
from pathlib import Path

from config import settings, logger
from networking.objects.partial_file import PartialFile


class DiskThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.files: queue.Queue[PartialFile] = queue.Queue()
        self.start()

    def run(self):
        logger.info("Background disk writer thread started")
        while True:
            partial_file = self.files.get()
            logger.info(f"Parsing {partial_file}")
            file = partial_file.to_file()
            logger.info(f"Started saving {file}")
            with open(os.path.join(str(Path(settings.output_folder)), file.path), 'wb') as f:
                f.write(file.bytes)
            logger.info(f"Saved {file}")
            self.files.task_done()
