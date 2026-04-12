from __future__ import annotations

import signal
import sys
import threading
from multiprocessing import Process
from multiprocessing.queues import Queue
from pathlib import Path
from threading import Thread

from src.common.config import settings, logger
from src.send.scanner import Scanner
from src.send.processor import Processor
import multiprocessing as mp

input_folder = settings.input_folder

def main():
    def handle_shutdown(sig=None, _=None):
        if mp.current_process().name != 'MainProcess':
            sys.exit(0)

        logger.success(f"Received signal {sig}, shutting down")
        for task in tasks:
            if isinstance(task, Process):
                task.terminate()
            task.join(timeout=1)

        shutdown_event.set()
        sys.exit()

    active_senders = mp.Value('i', 0)
    queues: dict[str, Queue[str]] = {str(folder.name): mp.Queue() for folder in Path(input_folder).iterdir() if
                                     folder.is_dir()}

    shutdown_event = threading.Event()
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    tasks: list[Thread | Process] = []
    for folder in queues:
        sender = Processor(folder, queues[folder], active_senders)
        tasks.append(sender)
        sender.start()

    scanner = Scanner(queues)
    tasks.append(scanner)
    scanner.start()

    while not shutdown_event.wait(timeout=1):
        for _task in tasks:
            if not _task.is_alive():
                logger.critical(f"{_task.name} crashed, shutting down")
                handle_shutdown()

if __name__ == "__main__":
    main()
