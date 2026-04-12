import errno
import socket
import time
import threading
from typing import Callable, TypeVar, Generic, Sized, Optional
import multiprocessing.sharedctypes as mp_types

from src.common.config import settings, logger
from src.common.packet import Packet
import queue

T = TypeVar('T', bound=Sized)

class CompletionTask:
    def __init__(self, func: Callable[[], None]):
        self.run = func

class Sender(threading.Thread, Generic[T]):
    buffer_size = settings.socket.get('buffer_size', 256_000_000)
    ip, port = settings.socket.ip, settings.socket.port
    sock: socket.socket

    def __init__(self, active_workers: 'mp_types.Synchronized'):
        super().__init__(name="Sender", daemon=True)
        self.queue: queue.Queue[T | CompletionTask] = queue.Queue(maxsize=settings.get("sender", {}).get("buffer_limit", 100_000_000) // Packet.packet_size)
        pacer_settings = settings.get("pacer", {})
        self.pacing_enabled = pacer_settings.get("enabled", False)
        if self.pacing_enabled:
            self.speed_limit = pacer_settings.speed_limit
            self.max_burst_time = pacer_settings.get('max_burst_time', 0.015)

        self.active_workers = active_workers

    def _setup(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.buffer_size)
        self.sock.connect((self.ip, self.port))

    def send_bytes(self, data: bytes):
        try:
            self.sock.send(data)
        except OSError as e:
            if e.errno in (errno.EBADF, errno.ENOTSOCK):
                raise e

    def run(self) -> None:
        with logger.catch(message="Unexpected error occurred, shutting down..."):
            self._setup()
            mode_text = ", with no speed limit"
            if self.pacing_enabled:
                mode_text = f", maintaining max speed of {self.speed_limit / 1000 ** 2:.2f}MB/s"
            logger.info(f"Sender started{mode_text}")

            is_active = False
            while True:
                try:
                    task = self.queue.get(timeout=1.0)
                except queue.Empty:
                    if self.pacing_enabled and is_active:
                        with self.active_workers.get_lock():
                            self.active_workers.value -= 1
                        is_active = False
                    continue

                if isinstance(task, CompletionTask):
                    task.run()
                    continue
                else:
                    packet = task

                if not self.pacing_enabled:
                    self.send_bytes(packet)
                    continue

                if not is_active:
                    with self.active_workers.get_lock():
                        self.active_workers.value += 1
                    is_active = True
                    time_credit = 0.0
                    last_time = time.perf_counter()

                now = time.perf_counter()
                time_credit += now - last_time
                last_time = now

                current_limit = self.speed_limit / max(1, self.active_workers.value)
                time_cost = len(packet) / current_limit

                if time_credit < time_cost:
                    time.sleep(time_cost - time_credit)

                self.send_bytes(packet)

                time_credit -= time_cost
                if time_credit > self.max_burst_time:
                    time_credit = self.max_burst_time

    def _submit(self, payload: T | CompletionTask):
        while True:
            try:
                self.queue.put(payload, timeout=1.0)
                return
            except queue.Full:
                if not self.is_alive():
                    raise RuntimeError(f"{self} crashed during file sending")

    def submit(self, payload: T):
        self._submit(payload)

    def call(self, callback: Callable[[], None]):
        self._submit(CompletionTask(callback))