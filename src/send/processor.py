from __future__ import annotations

import errno
import math, socket, time
import queue
import re
import signal
from multiprocessing import Process
from multiprocessing.queues import Queue
import multiprocessing.sharedctypes as mp_types
from pathlib import Path
from threading import Thread

import zfec

from src.common.config import settings, logger
from src.common.packet import Packet
from src.send.encoder import generate_packets, calc_k_m
from src.send.file import File
from src.send.sender import Sender

def to_camel_case(text):
    s = re.sub(r"([_\-])+", " ", text)
    s = s.title()
    s = s.replace(" ", "")
    return s


class Processor(Process):
    temp_folder = settings.temp_folder

    temp_path: Path
    sender: Sender
    threads: list[Thread]

    def __init__(self, folder: str, _queue: Queue[str], active_senders: 'mp_types.Synchronized'):
        super().__init__(name=f"{to_camel_case(folder)}Processor", daemon=True)
        self.folder = folder
        self.queue = _queue
        self.active_senders = active_senders

    def _setup(self):
        self.temp_path = Path(self.temp_folder)

        self.sender = Sender(self.active_senders)
        self.threads = [self.sender]
        for thread in self.threads:
            thread.start()

    def _threads_healthcheck(self):
        for thread in self.threads:
            if not thread.is_alive():
                logger.critical(f"{thread.name} is not running, shutting down...")
                return False
        return True

    class PassTracker:
        start_time: float

        def __init__(self, file: File, pass_num: int, passes: int):
            self.file = file
            self.pass_num = pass_num
            self.passes = passes

        def start_callback(self, first = True):
            def callback():
                if first:
                    logger.info(f"Started sending {self.file} pass {self.pass_num + 1}/{self.passes}")
                self.start_time = time.perf_counter()
            return callback

        def complete_callback(self, size: int, final = False):
            def callback():
                elapsed = time.perf_counter() - self.start_time
                if elapsed > 0:
                    if final:
                        log = logger.success
                    else:
                        log = logger.info
                    log(f"Sent {self.file} (pass {self.pass_num + 1}/{self.passes}) at "
                                f"{1 / (elapsed / size) / (1024 * 1024):.1f} MB/s")
            return callback

    def process_file(self, file: File):
        k, m = calc_k_m(len(file))
        passes = math.ceil(m/k)
        chunks_amount = math.ceil(len(file) / (k * Packet.payload_size))
        logger.info(
            f"Started processing {file} ({chunks_amount} chunks of {k} packets) with {int((m - k) / m * 100)}% redundancy")
        for pass_num in range(passes):
            size = 0
            tracker = Processor.PassTracker(file, pass_num, passes)
            self.sender.call(tracker.start_callback(first=pass_num == 0))
            for packet in generate_packets(file, pass_num):
                size += len(packet)
                self.sender.submit(bytes(packet))
            self.sender.call(tracker.complete_callback(size, final=pass_num+1==passes))

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        with logger.catch(message="Unexpected error occurred, shutting down..."):
            self._setup()
            logger.info(f"Processor for {self.folder} is running")

            while True:
                try:
                    file = self.queue.get(timeout=1.0)
                except queue.Empty:
                    # Checking for dying threads only when the Processor is not under heavy load
                    if not self._threads_healthcheck():
                        return
                    continue

                path = self.temp_path / file

                try:
                    self.process_file(File(file, self.temp_path))
                    path.unlink(missing_ok=True)
                except (OSError, ValueError, zfec.Error) as e:
                    if not path.exists():
                        logger.warning(f"Dropping {file} since it disappeared from {self.temp_path}")
                    else:
                        logger.warning(f"Error occurred while sending {file}. Re-queueing: {e}")
                        self.queue.put(file)
                        time.sleep(1)