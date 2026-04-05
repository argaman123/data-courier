from __future__ import annotations

import multiprocessing as mp
import signal
import sys
import threading
from multiprocessing import shared_memory
from multiprocessing.queues import Queue

from src.common.config import settings, logger
from src.common.packet import Packet
from src.receive.listener import Listener
from src.receive.processor import Processor

shm_name = settings.get('shm', {}).get('name', 'courier_send_shm')
shm_size = settings.get('shm', {}).get('size', 256_000_000)
def _create_shm():
    try:
        existing_shm = shared_memory.SharedMemory(name=shm_name)
        existing_shm.unlink()
        logger.warning(f"Cleaned leftover shared memory {shm_name}")
    except FileNotFoundError:
        pass
    return shared_memory.SharedMemory(create=True, name=shm_name, size=shm_size)

def main():
    def handle_shutdown(sig=None, _=None):
        if mp.current_process().name != 'MainProcess':
            sys.exit(0)

        logger.success(f"Received signal {sig}, shutting down")
        for proc in processes:
            proc.terminate()
            proc.join()

        shm.close()
        shm.unlink()
        shutdown_event.set()
        sys.exit()

    shm = _create_shm()
    # By reducing one spot I'm making sure I would never overlap the bytearray,
    # even when the listener is too fast compared to the processor
    offset_queue: Queue[tuple[int, int]] = \
        (mp.Queue(
            maxsize=int(shm.size // Packet.packet_size) - 1))
    processes = [
        Processor(offset_queue, shm.name),
        Listener(offset_queue, shm.name)
    ]
    shutdown_event = threading.Event()
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    for _proc in processes:
        _proc.start()

    while not shutdown_event.wait(timeout=1):
        for _proc in processes:
            if not _proc.is_alive():
                logger.critical(f"{_proc.name} crashed, shutting down")
                handle_shutdown()


if __name__ == "__main__":
   main()