import math
import struct
import threading
from enum import Enum
from typing import Self

from BinaryDataDecoder.utils import open_as_binary


class DataTypeMetaData:
    def __init__(self, priority_index: int, formatter_char: str, length_in_byte: int, endian_bitmask: int):
        self.priority_index = priority_index
        self.formatter_char = formatter_char
        self.endian_bitmask = endian_bitmask
        self.length_in_byte = length_in_byte
        full_bit_mask = 2 ** (8 * length_in_byte) - 1
        bitmask = full_bit_mask & endian_bitmask
        self.little_right_shift = 0
        while bitmask != 0 and bitmask % 2 == 0:  # Continue while n is even
            bitmask //= 2
            self.little_right_shift += 1
        self.bitmask = bitmask
        (math.ceil(math.log2(bitmask)) + 1)
        self.big_right_shift = length_in_byte * 8 - self.little_right_shift - math.floor(math.log2(bitmask)) - 1
        self.is_signed = ord(formatter_char) > 90

    @property
    def endian_bitmasks(self):
        return [(self.endian_bitmask, self.big_right_shift, ENDIAN.LITTLE_ENDIAN),
                (self.endian_bitmask, self.big_right_shift, ENDIAN.BIG_ENDIAN)]


class ENDIAN(Enum):
    BIG_ENDIAN = 'big'
    LITTLE_ENDIAN = 'little'


class FoundDataInfo:
    def __init__(self, offset: int, bytes_step: int, data_type: DataTypeMetaData, endian: ENDIAN):
        self.offset = offset
        self.bytes_step = bytes_step
        self.data_type = data_type
        self.endian = endian


class DATA_TYPE(Enum):
    # Priority index, Formatter, big endian, little endian
    DOUBLE = (0, 'd', 8, 0x7FF0000000000000)
    FLOAT = (1, 'f', 4, 0x7F800000)
    LONG_LONG = (2, 'q', 8, 0xFFFFFFFF00000000)
    U_LONG_LONG = (3, 'Q', 8, 0x7FFFFFFF80000000)
    INT = (4, 'i', 4, 0xFFFF0000)
    U_INT = (5, 'I', 4, 0x7FFF8000)
    SHORT = (6, 'q', 2, 0xFF00)
    U_SHOR_SHORT = (7, 'Q', 2, 0x7F80)
    CHAR = (8, 'b', 1, 0xF0)
    U_CHAR = (9, 'B', 1, 0xE1)

    @classmethod
    def prio_list(cls):
        for a in list(cls):
            yield a

    def data_type_meta_data(self) -> DataTypeMetaData:
        return DataTypeMetaData(*self.value)


class BinaryDataFinder():

    def __init__(self, file_path: str, chunk_size: int = 2 ** 8, number_of_threads: int = 5):
        self._fp = file_path
        self._file_handler = None
        self._number_of_threads = number_of_threads
        self._lock = threading.RLock()
        self._chunk_idx = 0
        self._chunks = None
        self._chunk_size = 2 ** math.ceil(math.log2(chunk_size))
        self._results: list[FoundDataInfo] = []

    def __del__(self):
        if self._file_handler is not None:
            self._file_handler.close()

    def find_data(self, data_types: list[DATA_TYPE] | None = None, endian: ENDIAN | None = None) -> Self:
        self._chunk_idx = 0
        self._chunks = open_as_binary(self._fp, 0, self._chunk_size)
        if data_types is None:
            data_types = DATA_TYPE.prio_list()
        elif isinstance(data_types, DATA_TYPE):
            data_types = [data_types]

        data_types = [d.data_type_meta_data() for d in data_types]
        data_types.sort(key=lambda a: a.priority_index)
        for data_type in data_types:
            threads = []
            for i in range(self._number_of_threads):
                t = threading.Thread(target=self._find_pattern, args=(data_type, endian))
                t.daemon = True
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

        return self

    def _next_chunk(self):
        with self._lock:
            if self._chunk_idx < len(self._chunks):
                idx = self._chunk_idx
                self._chunk_idx += 1
                return (self._chunks[idx], idx)
            else:
                return None

    @staticmethod
    def split_bytes(data: bytes, n: None | int = None, sep: int = 0):
        if n is None:
            return data
        return [data[i:i + n] for i in range(0, len(data), n + sep) if len(data[i:i + n]) == n]

    @staticmethod
    def shift_bytes(to_test, max_val):
        # Split the bytes object into chunks of size `n`
        remember = False
        new_vals = []
        for m in reversed(to_test):
            m = m << 1
            if remember:
                m += 1
            remember = m > max_val
            m %= max_val
            new_vals.append(m)
        return reversed(new_vals)

    @classmethod
    def _get_steps(cls, data_type: DATA_TYPE):
        pass

    def _find_pattern(self, data_type: DataTypeMetaData, endian_filter: None | ENDIAN, to_check: int = 10):

        while chunk_and_idx := self._next_chunk():
            chunk, chunk_idx = chunk_and_idx
            self._find_pattern_in_chunk(chunk, chunk_idx, data_type, to_check)

    def _find_pattern_in_chunk(self, chunk: bytes, chunk_idx: int, data_type: DataTypeMetaData,
                               to_check: int = 10, byte_shifts: int = 16):
        for byte_shift in range(byte_shifts):
            chunk_to_test = chunk[byte_shift:data_type.length_in_byte + byte_shift]
            for (bitmasks, right_shift, endian) in data_type.endian_bitmasks:

                bo = '!Q' if endian == ENDIAN.BIG_ENDIAN else '<Q'
                bin_to_test = struct.unpack(bo, chunk_to_test)[0]
                test_elem = (bin_to_test & bitmasks) >> right_shift
                for step in range(0, to_check * 8):
                    test_offset = data_type.length_in_byte + byte_shift + step
                    chunks_to_test = self.split_bytes(chunk[test_offset:], data_type.length_in_byte, step)
                    bins_to_test = [struct.unpack(bo, x)[0] for x in chunks_to_test[:4]]
                    step_check = True
                    for test_bin in bins_to_test:
                        res = abs(test_elem - ((test_bin & bitmasks) >> right_shift))
                        if res > 3:
                            step_check = False
                            break

                    if step_check:
                        if self._validate_result(b''.join(chunks_to_test), endian, data_type):
                            self._results.append(
                                FoundDataInfo(self._chunk_size * chunk_idx + byte_shift, step, data_type, endian)
                            )

    def _validate_result(self, chunk,  endian: ENDIAN, data_type: DataTypeMetaData):
        number_of_results = int(len(chunk) // data_type.length_in_byte)
        endian_char = '>' if endian == ENDIAN.BIG_ENDIAN else '<'
        result = struct.unpack(f'{endian_char}{number_of_results}{data_type.formatter_char}', chunk)
        result = [result[i + 1] - result[i] for i in range(len(result) - 1)]
        result = [result[i + 1] - result[i] for i in range(len(result) - 1)]
        return all(x < 5000 for x in result)


if __name__ == "__main__":
    # Convert an integer to bytes in big-endian and little-endian
    filename = 'test_files/MSPeak.bin'
    BinaryDataFinder(number_of_threads=1, file_path=filename).find_data()
