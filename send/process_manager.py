from config import settings, logger
import time
from multiprocessing import Pool, Manager
from objects.file import File

#prop func fot testing
def get_file():
    return File(str("."), bytes(".", encoding="utf-8"))

#prop func fot testing
def send_file(file):
    time.sleep(5)
    return "Done"


class WorkerPool:
    def __init__(self, num_processes):
        self.num_processes = num_processes
        self.pool = Pool(self.num_processes)

    def run(self, get_func, send_func):
        with Manager() as mgr:
            workstation_pool = mgr.Semaphore(self.num_processes)
            with self.pool as pool:
                while True:
                    self.wait_for_available_workstation(workstation_pool)
                    file = get_func()
                    pool.apply_async(self.clam_job, args=(workstation_pool, file, send_func,), error_callback=logger.error, callback=logger.info)
                    time.sleep(.1)

    @staticmethod
    def clam_job(workstation_pool, file, send_func):
        with workstation_pool:
            result = send_func(file)
        return result

    @staticmethod
    def wait_for_available_workstation(workstation_pool):
        workstation_pool.acquire()
        workstation_pool.release()



if __name__ == "__main__":
    WorkerPool(10).run(get_file, send_file)
