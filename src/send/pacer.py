import time
import multiprocessing.sharedctypes as mp_types
from src.common.config import settings, logger


class Pacer:
    def __init__(self, active_senders: 'mp_types.Synchronized'):
        if not settings.get("pacer") or not settings.get("pacer").get("enabled"):
            self.enabled = False
        else:
            self.enabled = True
            self.batch_limit = settings.pacer.batch_limit
            self.target_speed = settings.pacer.target_speed

            self.start_time = time.perf_counter()
            self.bytes_sent = 0
            self.active_senders = active_senders
            logger.info(f"Pacer module is enabled, maintaining {self.target_speed / 1000 ** 2:.2f}MB/s")

    def reset(self):
        self.bytes_sent = 0
        self.start_time = time.perf_counter()

    def wait_if_needed(self, size: int):
        if not self.enabled: return
        self.bytes_sent += size
        if self.bytes_sent >= self.batch_limit:
            elapsed_time = time.perf_counter() - self.start_time
            target_batch_time = (self.bytes_sent / self.target_speed) * self.active_senders.value
            if elapsed_time < target_batch_time:
                time.sleep(target_batch_time - elapsed_time)
            self.reset()