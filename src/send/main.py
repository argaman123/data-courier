from multiprocessing.queues import Queue
from pathlib import Path

from src.config import settings
from src.send.scanner import Scanner
from src.send.sender import Sender
import multiprocessing as mp

if __name__ == "__main__":
    active_senders = mp.Value('i', 0)
    queues: dict[str, Queue[str]] = {str(folder.name): mp.Queue() for folder in Path(settings.input_folder).iterdir() if folder.is_dir()}

    for folder in queues:
        sender = Sender(folder, queues[folder], active_senders)
        sender.start()

    scanner = Scanner(queues)
    scanner.start()
    scanner.join()