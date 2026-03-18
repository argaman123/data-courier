import multiprocessing
import signal
import threading
from multiprocessing import shared_memory
from multiprocessing.queues import Queue
from config import settings, logger
from objects.packet import Payload
from receive.listener import Listener
from receive.processor import Processor


class Receiver:
    def __init__(self, _id: str):
        self.id = _id
        self.shm = self._create_shm()
        # By reducing one spot I'm making sure I would never overlap the bytearray,
        # even when the listener is too fast compared to the processor
        self.offset_queue: Queue[tuple[int, int]] = \
            (multiprocessing.Queue(maxsize=settings.receiver_buffer_size // (settings.payload_size + Payload.header_size) - 1))
        self.processor = Processor(_id, self.offset_queue)
        self.listener = Listener(_id, self.offset_queue)
        self.shutdown_event = threading.Event()

    def _create_shm(self):
        shm_name = settings.shm_prefix + self.id
        try:
            existing_shm = shared_memory.SharedMemory(name=shm_name)
            existing_shm.unlink()
            logger.warning(f"Cleaned leftover shared memory {shm_name}")
        except FileNotFoundError:
            pass
        return shared_memory.SharedMemory(create=True, name=shm_name, size=settings.receiver_buffer_size)

    def _handle_shutdown(self, sig, frame):
        logger.info(f"Received signal {sig}, shutting down")
        for proc in [self.listener, self.processor]:
            proc.terminate()
            proc.join()

        self.shm.close()
        self.shm.unlink()
        self.shutdown_event.set()

    def start(self):
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        self.processor.start()
        self.listener.start()

        self.shutdown_event.wait()

if __name__ == "__main__":
    receiver = Receiver(str(settings.port))
    receiver.start()
