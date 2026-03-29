import signal
import sys
import threading
from multiprocessing.queues import Queue
from pathlib import Path

from src.config import settings, logger
from src.send.scanner import Scanner
from src.send.sender import Sender
import multiprocessing as mp

def _handle_shutdown(sig=None, _=None):
    logger.success(f"Received signal {sig}, shutting down")
    for proc in processes:
        proc.terminate()
        proc.join()

    shutdown_event.set()
    sys.exit()


if __name__ == "__main__":
    active_senders = mp.Value('i', 0)
    queues: dict[str, Queue[str]] = {str(folder.name): mp.Queue() for folder in Path(settings.input_folder).iterdir() if folder.is_dir()}

    shutdown_event = threading.Event()
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    processes = []
    for folder in queues:
        sender = Sender(folder, queues[folder], active_senders)
        processes.append(sender)
        sender.start()

    scanner = Scanner(queues)
    scanner.start()

    while not shutdown_event.wait(timeout=1):
        for _proc in processes:
            if not _proc.is_alive():
                logger.critical(f"{_proc.name} crashed, shutting down")
                _handle_shutdown()
