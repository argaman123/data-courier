import math
from functools import lru_cache

import zfec

from config import settings
from objects.file import File
from objects.packet import Packet


@lru_cache(maxsize=256)
def _get_encoder(k, m):
    return zfec.Encoder(k, m)

def calc_k_m(file_size: int):
    """
    Calculates the best fitting (k, m) for the provided file_size.
    Tries to keep the m/k ratio as close to packets_multiplier as possible, while maximizing chunk size and
    minimizing extra empty packets (needed for the algorithm to work)
    """
    total_packets = math.ceil(file_size / settings.payload_size)
    max_k = int(255 // settings.packets_multiplier) # 255 to keep it within byte range

    if total_packets <= max_k:
        k = total_packets
        return k, int(k * settings.packets_multiplier)

    best_k, min_extra_packets = max_k, max_k

    for k in range(max_k, max(1, int(max_k // 2)) - 1, -1):
        extra_packets = total_packets % k
        if min_extra_packets > extra_packets:
            min_extra_packets = extra_packets
            best_k = k

    return best_k, int(best_k * settings.packets_multiplier)

def generate_chunks(file: File, pass_num: int, max_chunks=settings.max_encoded_chunks):
    chunks: list[tuple[int, list]] = []
    k, m = calc_k_m(len(file))
    chunk_size = k * settings.payload_size
    encoder = _get_encoder(k, m)
    last_chunk = False
    for chunk_index, (offset, chunk_bytes) in enumerate(file.read(chunk_size)):
        if offset + chunk_size >= len(file):
            last_chunk = True
            # all payloads must keep the same size for the decoder to work properly
            if len(chunk_bytes) < chunk_size:
                chunk_bytes = bytes(chunk_bytes) + b'\x00' * (chunk_size - len(chunk_bytes))

        payloads = [chunk_bytes[i:i + settings.payload_size] for i in range(0, chunk_size, settings.payload_size)]

        start_packet, end_packet = pass_num * k, (pass_num + 1) * k
        # noinspection PyArgumentList
        encoded_payloads = encoder.encode(payloads)[start_packet:end_packet]
        chunks.append((chunk_index, encoded_payloads))

        if len(chunks) >= max_chunks or last_chunk:
            for _packet_index in range(k):
                for _chunk_index, _chunk in chunks:
                    if _packet_index < len(_chunk):
                        yield Packet(file.id, len(file), k, m, _chunk_index, _packet_index + start_packet, _chunk[_packet_index])
            chunks = []

