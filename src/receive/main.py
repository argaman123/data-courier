import multiprocessing as mp
import signal
import sys
import threading
from multiprocessing import shared_memory
from multiprocessing.queues import Queue

from src.config import settings, logger
from src.receive.listener import Listener
from src.receive.processor import Processor


def _create_shm():
    try:
        existing_shm = shared_memory.SharedMemory(name=settings.shm_name)
        existing_shm.unlink()
        logger.warning(f"Cleaned leftover shared memory {settings.shm_name}")
    except FileNotFoundError:
        pass
    return shared_memory.SharedMemory(create=True, name=settings.shm_name, size=settings.receiver_buffer_size)


def _handle_shutdown(sig=None, _=None):
    logger.info(f"Received signal {sig}, shutting down")
    for proc in processes:
        proc.terminate()
        proc.join()

    shm.close()
    shm.unlink()
    shutdown_event.set()
    sys.exit()


if __name__ == "__main__":
    shm = _create_shm()
    # By reducing one spot I'm making sure I would never overlap the bytearray,
    # even when the listener is too fast compared to the processor
    offset_queue: Queue[tuple[int, int]] = \
        (mp.Queue(
            maxsize=int(settings.receiver_buffer_size // Listener.packet_size) - 1))
    processes = [
        Processor(offset_queue),
        Listener(offset_queue)
    ]
    shutdown_event = threading.Event()
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    for _proc in processes:
        _proc.start()

    while not shutdown_event.wait(timeout=1):
        for _proc in processes:
            if not _proc.is_alive():
                logger.critical(f"{_proc.name} crashed, shutting down")
                _handle_shutdown()
