from __future__ import annotations

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
        self.file_scan_interval = settings.file_scan_interval
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
            
            self._move_and_queue_file(file, self.input_folder)
            
        except FileNotFoundError:
            pass

    def _move_file(self, file: Path, source_path: Path):
        try:
            target = self.temp_folder / file.relative_to(source_path)
            logger.debug(f"Moving {file} to {self.temp_folder}")
            if source_path != self.temp_folder and target.exists():
                logger.debug(f"{file} already exists in {self.temp_folder}, skipping for now...")
                return
            target.parent.mkdir(exist_ok=True)
            shutil.move(str(file), str(target))
            self._queue_file(target, self.temp_folder)
            del self.files[file]
        except (OSError, IOError) as e:
            logger.debug(f"{file} is still being modified, skipping for now... {e}")

    def _queue_file(self, file: Path, source_path: Path):
        logger.info(f"Queueing {file}")
        self.queues[file.parent.name].put(str(file.relative_to(source_path)))

    def _requeue_temp_folder(self):
        for file in self.temp_folder.iterdir():
            logger.info(f"Re-queueing {file}")
            self._queue_file(file, self.temp_folder)


    def run(self):
        self.files = {}
        logger.info(f"Started scanning {self.input_folder}")
        self._requeue_temp_folder()
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
                logger.error(f"Error while scanning {self.input_folder}: {e}")

            time.sleep(self.file_scan_interval)
