import threading
import queue
import logging
from pathlib import Path

from config import settings
from networking.objects.partial_file import PartialFile


class DiskThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.files: queue.Queue[PartialFile] = queue.Queue()
        self.start()

    def run(self):
        logging.info("Background disk writer thread started")
        while True:
            partial_file = self.files.get()
            logging.info(f"Parsing {partial_file}")
            file = partial_file.to_file()
            logging.info(f"Started saving {file}")
            file.save(str(Path(settings.output_folder)))
            logging.info(f"Saved {file}")
            self.files.task_done()
