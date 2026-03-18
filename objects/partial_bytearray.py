import math
from config import settings
from objects.packet import Packet


class PartialByteArray:
    def __init__(self):
        self.file_size = 0
        self.bytes_received = 0
        self.arrived: bytearray | None = None
        self.bytearray: bytearray | None = None

    def is_complete(self):
        return 0 < self.file_size == self.bytes_received

    def insert(self, packet: Packet):
        if self.file_size == 0:
            self.file_size = packet.total_size
            self.bytearray = bytearray(self.file_size)
            self.arrived = bytearray(math.ceil(self.file_size / settings.chunk_size))

        index = packet.offset // settings.chunk_size
        if not self.arrived[index]:
            self.bytearray[packet.offset:packet.offset + len(packet.payload)] = packet.payload
            self.bytes_received += len(packet.payload)
            self.arrived[index] = True

    def to_bytes(self):
        return self.bytearray

    def __str__(self):
        return f"({self.bytes_received // settings.chunk_size} / {self.file_size // settings.chunk_size})"