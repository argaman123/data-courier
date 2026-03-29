import time
import shutil
from multiprocessing.queues import Queue
from pathlib import Path
from threading import Thread

from src.config import settings, logger


class Scanner(Thread):
    def __init__(self, queues: dict[str, Queue[str]]):
        super().__init__(name="Scanner", daemon=True)
        self.input_folder = Path(settings.input_folder)
        self.temp_folder = Path(settings.temp_folder)
        self.file_changed_time = settings.file_changed_time
        self.file_scan_delay = settings.file_scan_delay
        self.queues = queues
        self.folders: list[Path] = [self.input_folder / folder for folder in queues.keys()]
        self.files = {}

    @staticmethod
    def _sample_file(path: Path):
        stats = path.stat()
        return stats.st_mtime, stats.st_size

    @staticmethod
    def _is_locked(file: Path):
        try:
            with file.open("a"):
                pass
            file.rename(file)
            return False
        except (OSError, IOError):
            return True

    def _process_file(self, file: Path):
        try:
            if file not in self.files:
                logger.debug(f"Found {file}")
                self.files[file] = self._sample_file(file)
                return

            current_time = time.time()
            if current_time - self.files[file][0] < self.file_changed_time:
                return

            current_sample = self._sample_file(file)
            if current_sample != self.files[file][1]:
                self.files[file] = current_time, current_sample
                logger.debug(f"{file} is still being written ({current_sample}), skipping for now...")
                return

            if self._is_locked(file):
                logger.debug(f"{file} is locked, skipping for now...")
                return

            target_path = self.temp_folder / str(file.relative_to(self.input_folder))
            if target_path.exists():
                logger.debug(f"{file} already exists in {self.temp_folder}, skipping for now...")
                return
            
            self._move_and_queue_file(file, target_path)
            
        except FileNotFoundError:
            pass

    def _move_and_queue_file(self, file: Path, target: Path):
        try:
            logger.debug(f"Moving {file} to {self.temp_folder}")
            target.parent.mkdir(exist_ok=True)
            shutil.move(str(file), str(target))
            self.queues[file.parent.name].put(str(file.relative_to(settings.input_folder)))
            logger.info(f"Queueing {target}")
            del self.files[file]
        except (OSError, IOError) as e:
            logger.debug(f"{file} is still being modified, skipping for now... {e}")

    def run(self):
        self.files = {}
        logger.info(f"Started scanning {self.input_folder} for new self.files")
        while True:
            try:
                current_files = set()
                for folder in self.folders.copy():
                    try:
                        for path in folder.iterdir():
                            if path.is_file():
                                current_files.add(path)
                                self._process_file(path)
                    except FileNotFoundError:
                        self.folders.remove(folder)

                # Clean manually deleted files
                for path in self.files:
                    if path not in current_files:
                        del self.files[path]
            except RuntimeError as e:
                logger.error(f"{e}")

            time.sleep(self.file_scan_delay)
