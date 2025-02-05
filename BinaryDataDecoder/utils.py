import math
import os.path
from itertools import product


def find_unused_2byte_pair(data: bytes) -> bytes | None:
    seen = {data[i:i + 2] for i in range(len(data) - 1)}  # All existing 2-byte pairs

    for b1, b2 in product(range(256), repeat=2):  # Iterate over all 65536 combinations
        pair = bytes([b1, b2])
        if pair not in seen:
            return pair  # Return the first unused 2-byte pair

    return None  # This should never happen unless all pairs are used


def open_as_binary(filename: str, offset: int = 0) -> bytes:
    with open(filename, 'rb') as f:
        return b''.join(f.readlines())[offset:]


def open_as_binary_lines(filename: str, offset: int = 0, n_bytes: int = 8, n_parts: int = -1) -> list[bytes]:
    lines = open_as_binary(filename, offset)
    return bytes_as_binary_lines(lines, n_bytes, n_parts)


def bytes_as_binary_lines(lines: bytes, n_bytes: int = 8, n_parts: int = -1):
    split_lines = []
    if n_parts > 0:
        n_bytes = math.ceil(len(lines) / n_parts)
    for i in range(0, len(lines), n_bytes):
        split_lines.append(lines[i:i + n_bytes])
    return split_lines


RESULT_DIR = os.path.join(f'binary_data_decoder')
os.makedirs(RESULT_DIR, exist_ok=True)

def lines_replace_read(lines: list[bytes], to_remove: list[tuple[int, int, int, int]],
                        replacement: bytes) -> bytes:
    lines = bytearray(b''.join(lines))


    for (start, stop, size, step) in to_remove:
        replacement_space = replacement * (size // 2)
        while start <= stop:
            lines[start:start + size] = replacement_space
            start += size + step

    return bytes(lines)
