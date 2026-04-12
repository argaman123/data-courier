import threading
from collections import deque
from typing import TypeVar, Generic, Sized

T = TypeVar('T', bound=Sized)

class SizedQueue(Generic[T]):
    class Full(Exception):
        pass

    def __init__(self, max_bytes: int):
        self.max_bytes = max_bytes
        self.current_bytes = 0
        self.queue: deque[T] = deque()
        self.condition = threading.Condition()


    def full(self):
        with self.condition:
            return self.current_bytes >= self.max_bytes

    def _add_item(self, item: T):
        self.queue.append(item)
        self.current_bytes += len(item)
        self.condition.notify()

    def put(self, item: T):
        with self.condition:
            while self.full():
                self.condition.wait()

            self._add_item(item)


    def put_nowait(self, item: T):
        with self.condition:
            if self.full():
                raise SizedQueue.Full()

            self._add_item(item)

    def get(self):
        with self.condition:
            while not self.queue:
                self.condition.wait()

            item = self.queue.popleft()
            self.current_bytes -= len(item)

            self.condition.notify_all()
            return item