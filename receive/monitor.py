import abc
import multiprocessing
import threading
import time

from config import logger, settings


# TODO <editor-fold desc="REMOVE MONITOR IN PROD">
class MonitoredProcess(multiprocessing.Process, abc.ABC):
    def __init__(self, monitor_rate=None, **kwargs):
        super().__init__(**kwargs)
        if monitor_rate is None:
            monitor_rate = settings.monitor_rate
        if not monitor_rate:
            self.enabled = False
        else:
            self.enabled = True
            self.bytes_counter = multiprocessing.Value('Q', 0, lock=False)
            self.monitor_rate = settings.monitor_rate
            threading.Thread(target=self._monitor, daemon=True, name=self.name).start()


    def _monitor(self):
        logger.info(f"Monitoring this process every {self.monitor_rate}s")
        while True:
            time.sleep(self.monitor_rate)
            value = self.bytes_counter.value
            self.bytes_counter.value = 0
            rate = round(value / (1024 * 1024) / self.monitor_rate, 1)
            if rate > 0:
                logger.debug(f"{rate} MB/s")

    def notify_monitor(self, amount: int):
        if self.enabled:
            self.bytes_counter.value += amount
# TODO </editor-fold>