import math
from functools import lru_cache

import zfec

from config import settings
from objects.packet import Packet


class Decoder:
    max_packet_index_distance = 0

    def __init__(self):
        self.decoder: zfec.Decoder | None = None
        self.file_size = 0
        self.bytearray: bytearray | None = None
        self.chunks: dict[int, dict[int, bytes]] = {}
        self.arrived: bytearray | None = None
        self.chunks_arrived = 0
        self.total_chunks = 0

    def is_complete(self):
        return 0 < self.chunks_arrived == self.total_chunks

    def process(self, packet: Packet):
        if self.file_size == 0:
            self.decoder = self._get_decoder(packet.k, packet.m)
            self.file_size = packet.file_size
            self.total_chunks = math.ceil(self.file_size / (packet.k * settings.payload_size))
            self.bytearray = bytearray(self.file_size)
            self.arrived = bytearray(self.total_chunks)

        if self.arrived[packet.chunk_index]:
            return

        if packet.chunk_index not in self.chunks:
            self.chunks[packet.chunk_index] = {}
        chunk = self.chunks[packet.chunk_index]

        if packet.packet_index not in chunk:
            chunk[packet.packet_index] = packet.payload

            if len(chunk) == packet.k:
                # TODO REMOVE max_packet_index_distance IN PRODUCTION
                self.max_packet_index_distance = max(self.max_packet_index_distance, packet.packet_index - packet.k)
                payload_list = self.decoder.decode(tuple(chunk.values()), tuple(chunk.keys()))
                offset = packet.chunk_index * (packet.k * settings.payload_size)
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

    @staticmethod
    @lru_cache(maxsize=256)
    def _get_decoder(k, m):
        return zfec.Decoder(k, m)

    def to_bytes(self):
        return self.bytearray

    def __str__(self):
        return f"({self.chunks_arrived} / {self.total_chunks} chunks)"