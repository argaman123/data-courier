from __future__ import annotations

import time
import shutil
from multiprocessing.queues import Queue
from pathlib import Path
from threading import Thread

from src.common.config import settings, logger


class Scanner(Thread):
    input_folder = settings.input_folder
    temp_folder = settings.temp_folder
    file_ready_delay = settings.get('scanner', {}).get('file_ready_delay', 1)
    folder_polling_interval = settings.get('scanner', {}).get('folder_polling_interval', 1)

    def __init__(self, queues: dict[str, Queue[str]]):
        super().__init__(name="Scanner", daemon=True)
        self.input = Path(self.input_folder)
        self.temp = Path(self.temp_folder)

        self.queues = queues
        self.folders: list[Path] = [self.input / folder for folder in queues.keys()]
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

    def _check_file(self, file: Path):
        try:
            if file not in self.files:
                logger.debug(f"Found {file}")
                self.files[file] = self._sample_file(file)
                return False

            current_time = time.time()
            if current_time - self.files[file][0] < self.file_ready_delay:
                return False

            current_sample = self._sample_file(file)
            if current_sample != self.files[file][1]:
                self.files[file] = current_time, current_sample
                logger.debug(f"{file} is still being written ({current_sample}), skipping for now...")
                return False

            if self._is_locked(file):
                logger.debug(f"{file} is locked, skipping for now...")
                return False
        except FileNotFoundError:
            return False
        return True

    def _move_and_queue_file(self, file: Path, source_path: Path):
        try:
            target = self.temp / file.relative_to(source_path)
            logger.debug(f"Moving {file} to {self.temp}")
            if source_path != self.temp and target.exists():
                logger.debug(f"{file} already exists in {self.temp}, skipping for now...")
                return
            target.parent.mkdir(exist_ok=True)
            shutil.move(str(file), str(target))
            self._queue_file(target, self.temp)
            del self.files[file]
        except (OSError, IOError) as e:
            logger.debug(f"{file} is still being modified, skipping for now... {e}")

    def _queue_file(self, file: Path, source_path: Path):
        relative_path = str(file.relative_to(source_path))
        logger.info(f"Queueing {relative_path}")
        self.queues[file.parent.name].put(relative_path)

    def _requeue_temp_folder(self):
        for folder in self.queues.keys():
            source_dir = (self.temp / folder)
            if not source_dir.is_dir():
                continue
            for path in source_dir.iterdir():
                if path.is_file():
                    logger.debug(f"Found existing {path}")
                    self._queue_file(path, self.temp)


    def run(self):
        self.files = {}
        logger.info(f"Started scanning {self.input}")
        self._requeue_temp_folder()
        while True:
            current_files = set()
            for folder in self.folders.copy():
                try:
                    for path in folder.iterdir():
                        try:
                            if path.is_file():
                                current_files.add(path)
                                if self._check_file(path):
                                    self._move_and_queue_file(path, self.input)
                        except (OSError, RuntimeError) as e:
                            logger.warning(f"Error while checking {path}: {e}")
                except FileNotFoundError:
                    logger.info(f"Stopped scanning {folder}, since it no longer exists")
                    self.folders.remove(folder)
                except OSError as e:
                    logger.warning(f"Error while scanning {folder}: {e}")
            # Clean manually deleted files
            for path in list(self.files.keys()):
                if path not in current_files:
                    del self.files[path]
            time.sleep(self.folder_polling_interval)
