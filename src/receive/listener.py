import queue
import signal
import socket
from multiprocessing import shared_memory, Process
from multiprocessing.queues import Queue
from src.config import settings, logger
from src.objects.packet import Packet


class Listener(Process):
    packet_size = settings.payload_size + Packet.header_size

    def __init__(self, offset_queue: Queue[tuple[int, int]]):
        super().__init__(name=f"Listener", daemon=True)
        self.offset_queue = offset_queue

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        shm = shared_memory.SharedMemory(name=settings.shm_name)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, settings.socket_buffer_size)
        sock.bind((settings.ip, settings.port))

        logger.info(f"Listener is running on {settings.ip}:{settings.port}")
        offset = 0
        while True:
            size = sock.recv_into(shm.buf[offset: offset + self.packet_size])
            data = (offset, size)
            try:
                self.offset_queue.put_nowait(data)
            except queue.Full:
                logger.warning("Processor is too slow, waiting for it to catch up..")
                self.offset_queue.put(data)

            offset = (offset + size) % shm.size
            if offset + self.packet_size >= shm.size:
                offset = 0

            self.notify_monitor(size)