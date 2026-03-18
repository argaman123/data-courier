import time

from config import settings, logger


class Pacer:
    def __init__(self):
        if not settings.pacer_target_speed:
            self.enabled = False
        else:
            self.enabled = True
            self.start_time = time.perf_counter()
            self.packets_sent = 0
            self.batch_size = settings.pacer_batch_size
            self.target_batch_time = (self.batch_size * settings.payload_size) / settings.pacer_target_speed
            logger.info(f"Pacer initialized {self.target_batch_time:.3f}s / {self.batch_size} packets")

    def reset(self):
        self.packets_sent = 0
        self.start_time = time.perf_counter()

    def wait_if_needed(self):
        if not self.enabled: return
        self.packets_sent += 1
        if self.packets_sent == self.batch_size:
            elapsed_time = time.perf_counter() - self.start_time
            if elapsed_time < self.target_batch_time:
                logger.debug("Process it too fast, manually throttling...")
                time.sleep(self.target_batch_time - elapsed_time)
            self.reset()