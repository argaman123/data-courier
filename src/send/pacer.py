import time
import multiprocessing.sharedctypes as mp_types
from src.config import settings


class Pacer:
    def __init__(self, active_senders: 'mp_types.Synchronized'):
        if not settings.pacer_target_speed:
            self.enabled = False
        else:
            self.enabled = True
            self.start_time = time.perf_counter()
            self.packets_sent = 0
            self.batch_size = settings.pacer_batch_size
            self.active_senders = active_senders

    def reset(self):
        self.packets_sent = 0
        self.start_time = time.perf_counter()

    def wait_if_needed(self):
        if not self.enabled: return
        self.packets_sent += 1
        if self.packets_sent == self.batch_size:
            elapsed_time = time.perf_counter() - self.start_time
            target_batch_time = ((self.batch_size * settings.payload_size) / settings.pacer_target_speed) * self.active_senders.value
            if elapsed_time < target_batch_time:
                time.sleep(target_batch_time - elapsed_time)
            self.reset()