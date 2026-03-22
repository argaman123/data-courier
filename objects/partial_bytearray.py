import math
import zfec
from config import settings, logger
from objects.packet import Packet
from send.sender import Sender


class PartialByteArray:
    decoder = zfec.Decoder(Sender.minimum_packets, Sender.total_packets)

    def __init__(self):
        self.file_size = 0
        self.bytearray: bytearray | None = None
        self.chunks: dict[int, dict[int, bytes]] = {}
        self.arrived: bytearray | None = None
        self.total_chunks = 0
        self.chunks_arrived = 0

    def is_complete(self):
        return 0 < self.chunks_arrived == self.total_chunks

    def insert(self, packet: Packet):
        if self.file_size == 0:
            self.file_size = packet.file_size
            self.total_chunks = math.ceil(self.file_size / Sender.chunk_size)
            self.bytearray = bytearray(self.file_size)
            self.arrived = bytearray(self.total_chunks)

        if self.arrived[packet.chunk_index]:
            return
            
        if packet.chunk_index not in self.chunks:
            self.chunks[packet.chunk_index] = {}
        chunk = self.chunks[packet.chunk_index]
        
        if packet.packet_id not in chunk:
            chunk[packet.packet_id] = packet.payload
            
            if len(chunk) == Sender.minimum_packets:
                payload_list = self.decoder.decode(tuple(chunk.values()), tuple(chunk.keys()))
                offset = packet.chunk_index * Sender.chunk_size
                for raw_payload in payload_list:
                    if offset + len(raw_payload) > self.file_size:
                        payload = raw_payload[:self.file_size - offset]
                    else:
                        payload = raw_payload
                    self.bytearray[offset:offset + len(payload)] = payload
                    offset += len(payload)

                del self.chunks[packet.chunk_index]
                self.arrived[packet.chunk_index] = True
                self.chunks_arrived += 1

    def to_bytes(self):
        return self.bytearray

    def __str__(self):
        return f"({self.chunks_arrived} / {self.total_chunks} chunks)"