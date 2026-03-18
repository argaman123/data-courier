import multiprocessing
import sys
import threading

from loguru import logger

max_context_size = 0

def add_context(record):
    global max_context_size
    thread_name = threading.current_thread().name
    if thread_name != "MainThread":
        max_context_size = max(max_context_size, len(thread_name))
        record["extra"]["thread"] = f"{thread_name: <{max_context_size}}"
        record["extra"]["proc"] = ""
    else:
        proc_name = multiprocessing.current_process().name
        max_context_size = max(max_context_size, len(proc_name))
        record["extra"]["thread"] = ""
        record["extra"]["proc"] = f"{proc_name: <{max_context_size}}"

def setup_logger(level: str):
    logger.remove()
    logger.add(sys.stdout, colorize=True, level=level,
               format="<green>{time:HH:mm:ss.SSS}</green> | "
                      "<magenta>{extra[proc]}</magenta><cyan>{extra[thread]}</cyan> | "
                      "<level>{level}</level> | "
                      "{message}")

    # logger.add("data-courier.log", colorize=False, rotation="500 MB")
    return logger.patch(add_context)
