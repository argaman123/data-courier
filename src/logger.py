import multiprocessing as mp
import sys
import threading

from loguru import logger


def add_context(record):
    record["extra"]["thread"] = ""
    record["extra"]["proc"] = ""

    thread_name = threading.current_thread().name
    proc_name = mp.current_process().name
    if proc_name != "MainProcess":
        record["extra"]["proc"] = proc_name
    if thread_name != "MainThread":
        thread = thread_name
        if record["extra"]["proc"]:
            thread = "->" + thread
        record["extra"]["thread"] = thread

def setup_logger(level: str):
    logger.remove()
    logger.add(sys.stdout, colorize=True, level=level,
               format="<green>{time:HH:mm:ss.SSS}</green> | "
                      "<magenta>{extra[proc]}</magenta><cyan>{extra[thread]}</cyan> | "
                      "<level>{level}</level> | "
                      "{message}")

    # logger.add("data-courier.log", colorize=False, rotation="500 MB")
    return logger.patch(add_context)
