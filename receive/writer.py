import threading, queue
from pathlib import Path

from config import settings, logger
from receive.partial_file import PartialFile
from receive.testing import test_and_reset


class Writer(threading.Thread):
    def __init__(self, _id: str, processor):
        super().__init__()
        self.name = "Writer-" + _id
        self.daemon = True
        self.files: queue.Queue[PartialFile] = queue.Queue()
        # TODO <editor-fold desc="REMOVE PROCESSOR REFERENCE IN PROD">
        self.processor = processor
        # TODO </editor-fold>

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

            # TODO <editor-fold desc="REMOVE INFO FILE IN PROD">
            if path == "info.json":
                test_and_reset(self.processor)
            # TODO </editor-fold>
