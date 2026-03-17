import time

from config import settings, logger


class Pacer:
    def __init__(self):
        if not settings.pacer_target_speed:
            self.disabled = True
        else:
            self.start_time = time.perf_counter()
            self.packets_sent = 0
            self.target_batch_time = (settings.batch_size * settings.chunk_size) / settings.pacer_target_speed
            logger.info(f"Pacer initialized {self.target_batch_time:.3f}s / {settings.batch_size} packets")

    def reset(self):
        self.packets_sent = 0
        self.start_time = time.perf_counter()

    def wait_if_needed(self):
        if self.disabled: return
        self.packets_sent += 1
        if self.packets_sent == settings.batch_size:
            elapsed_time = time.perf_counter() - self.start_time
            if elapsed_time < self.target_batch_time:
                time.sleep(self.target_batch_time - elapsed_time)
            self.reset()