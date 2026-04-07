import math
from functools import lru_cache

import zfec

from src.common.packet import Packet
from src.send.file import File


class PartialFile:
    def __init__(self, packet: Packet):
        self.file_id = packet.file_id
        self.decoder = self._get_decoder(packet.k, packet.m)
        self.file_size = packet.file_size
        self.bytearray = bytearray(self.file_size)

        self.total_chunks = math.ceil(self.file_size / (packet.k * Packet.payload_size))
        self.chunks_arrived = bytearray(self.total_chunks)
        self.chunks: dict[int, dict[int, bytes]] = {}
        self.chunks_arrived_amount = 0

        # For logging purposes
        self.missing_packets = 0
        self.max_missing_packets = 0

    @property
    def complete(self):
        return self.file_id is not None and self.chunks_arrived_amount == self.total_chunks

    def free_memory(self):
        if self.chunks: del self.chunks
        if self.chunks_arrived: del self.chunks_arrived
        if self.bytearray: del self.bytearray

    def to_file(self):
        return File.extract_header(self.bytearray)

    def process(self, packet: Packet):
        if self.chunks_arrived[packet.chunk_index]:
            return self.complete

        if packet.chunk_index not in self.chunks:
            self.chunks[packet.chunk_index] = {}

        chunk = self.chunks[packet.chunk_index]
        chunk[packet.packet_index] = packet.payload

        if len(chunk) == packet.k:
            missing_packets = (packet.packet_index + 1) - packet.k
            if missing_packets > 0:
                self.missing_packets += missing_packets
                self.max_missing_packets = max(self.max_missing_packets, missing_packets)
            payload_list = self.decoder.decode(tuple(chunk.values()), tuple(chunk.keys()))
            offset = packet.chunk_index * (packet.k * Packet.payload_size)
            for raw_payload in payload_list:
                if offset + len(raw_payload) > self.file_size:
                    payload = raw_payload[:self.file_size - offset]
                else:
                    payload = raw_payload
                self.bytearray[offset:offset + len(payload)] = payload
                offset += len(payload)

            del self.chunks[packet.chunk_index]
            self.chunks_arrived[packet.chunk_index] = True
            self.chunks_arrived_amount += 1

        return self.complete

    @staticmethod
    @lru_cache(maxsize=256)
    def _get_decoder(k, m):
        return zfec.Decoder(k, m)

    def __str__(self):
        missing_text = ""
        if self.missing_packets > 0:
            missing_text = f", worst chunk had ~{self.max_missing_packets} missing packets for a total of ~{self.missing_packets}"
        return f"[{self.file_id.hex()}] ({self.chunks_arrived_amount}/{self.total_chunks} chunks)" + missing_text

    def __len__(self):
        return self.file_size