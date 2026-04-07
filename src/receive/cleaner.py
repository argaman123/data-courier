import time
from threading import Thread, Lock

from src.common.config import logger, settings
from src.receive.partial_file import PartialFile


class Cleaner(Thread):
    partial_file_expiry = settings.get('cleaner', {}).get('partial_file_expiry', 60)

    def __init__(self, processing: dict[bytes, PartialFile]):
        super().__init__(name="Cleaner", daemon=True)
        self.processing = processing
        self.files: dict[bytes, bool] = {}
        self.lock = Lock()

    def register(self, file_id: bytes):
        with self.lock:
            self.files[file_id] = True

    def run(self):
        with logger.catch(message="Unexpected error occurred, shutting down..."):
            logger.info("Background memory cleaner started")
            while True:
                deleted_files: list[PartialFile] = []
                with self.lock:
                    for file_id in list(self.files.keys()):
                        if self.files[file_id]:
                            self.files[file_id] = False
                        else:
                            deleted_file = self.processing.pop(file_id, None)
                            if deleted_file:
                                deleted_files.append(deleted_file)
                            del self.files[file_id]
                for file in deleted_files:
                    if not file.complete:
                        logger.warning(f"Received incomplete file {file}")
                        file.free_memory()
                    else:
                        logger.debug(f"Cleaning completed {file}")
                time.sleep(self.partial_file_expiry)