import math
from functools import lru_cache

import zfec

from src.common.config import settings
from src.send.file import File
from src.common.packet import Packet


@lru_cache(maxsize=256)
def _get_encoder(k, m):
    return zfec.Encoder(k, m)

_encoder_settings = settings.get('encoder', {})
packets_multiplier = _encoder_settings.get('packets_multiplier', 1)
encoder_buffer_limit = _encoder_settings.get('buffer_limit', None)
enlarge_tiny_files = _encoder_settings.get('enlarge_tiny_files', True)

def calc_k_m(file_size: int):
    """
    Calculates the best fitting (k, m) for the provided file_size.
    Maximizes k while minimizing extra empty packets needed the last chunk for smaller files.
    """
    total_packets = math.ceil(file_size / Packet.payload_size)

    max_k = int(256 / packets_multiplier)
    if total_packets < max_k:
        if enlarge_tiny_files:
            k = math.ceil(max_k / 2)
        else:
            k = total_packets
    else:
        k = math.ceil(total_packets / math.ceil(total_packets / max_k))
    return k, int(k * packets_multiplier)

def generate_packets(file: File, pass_num: int):
    chunks: list[tuple[int, list]] = []
    k, m = calc_k_m(len(file))
    chunk_size = k * Packet.payload_size
    encoder = _get_encoder(k, m)
    last_chunk = False
    for chunk_index, (offset, chunk_bytes) in enumerate(file.read(chunk_size)):
        if offset + chunk_size >= len(file):
            last_chunk = True
            if len(chunk_bytes) < chunk_size:
                chunk_bytes = bytes(chunk_bytes).ljust(chunk_size)

        payloads = [chunk_bytes[i:i + Packet.payload_size] for i in range(0, chunk_size, Packet.payload_size)]

        start_packet, end_packet = pass_num * k, (pass_num + 1) * k
        # noinspection PyArgumentList
        encoded_payloads = encoder.encode(payloads)[start_packet:end_packet]
        chunks.append((chunk_index, encoded_payloads))
        if (encoder_buffer_limit is not None and chunk_size * len(chunks) >= encoder_buffer_limit) or last_chunk:
            for _packet_index in range(k):
                for _chunk_index, _chunk in chunks:
                    if _packet_index < len(_chunk):
                        yield Packet(file.id, len(file), k, m, _chunk_index, _packet_index + start_packet, _chunk[_packet_index])
            chunks.clear()

