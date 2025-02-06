import json
import math
from enum import Enum
from typing import Self


class ENDIAN(Enum):
    BIG_ENDIAN = 'big'
    LITTLE_ENDIAN = 'little'


class DataTypeMetaData:
    def __init__(self, priority_index: int, formatter_char: str, length_in_byte: int, endian_bitmask: int):
        self.priority_index = priority_index
        self.formatter_char = formatter_char
        self.endian_bitmask = endian_bitmask
        self.length_in_byte = length_in_byte
        full_bit_mask = 2 ** (8 * length_in_byte) - 1
        bitmask = full_bit_mask & endian_bitmask
        self._right_shift = 0
        while bitmask != 0 and bitmask % 2 == 0:  # Continue while n is even
            bitmask //= 2
            self._right_shift += 1
        self.bitmask = bitmask
        self.is_signed = ord(formatter_char) > 90
        self.is_signed_integer = formatter_char not in ['d', 'f'] and self.is_signed
        
    def decrease_accuracy(self):
        if self.bitmask > 0xF:
            self._right_shift += 1
            self.bitmask //= 2
            self.endian_bitmask &= (self.endian_bitmask // 2)

    def __str__(self):
        return f'{self.length_in_byte} {self.formatter_char}'

    def parse_byte_stream_test_seq(self, chunk_to_test: bytes, endian: ENDIAN):
        if endian == ENDIAN.LITTLE_ENDIAN:
            return self._parse_byte_stream_test_seq_little(chunk_to_test)
        return self._parse_byte_stream_test_seq_big(chunk_to_test)

    def _parse_byte_stream_test_seq_big(self, chunk_to_test: bytes):
        bin_to_test = int.from_bytes(chunk_to_test, 'big')
        return (bin_to_test & self.endian_bitmask) >> self._right_shift

    def _parse_byte_stream_test_seq_little(self, chunk_to_test: bytes):
        bin_to_test = int.from_bytes(chunk_to_test, 'little')
        return (bin_to_test & self.endian_bitmask) >> self._right_shift

    def __dict__(self):
        return {
            'priority_index': self.priority_index,
            'formatter_char': self.formatter_char,
            'length_in_byte': self.length_in_byte,
            'endian_bitmask': self.endian_bitmask,
        }

    @property
    def endian_bitmasks(self):
        return [(self._parse_byte_stream_test_seq_little, ENDIAN.LITTLE_ENDIAN),
                (self._parse_byte_stream_test_seq_big, ENDIAN.BIG_ENDIAN)]


class FoundDataInfo:

    @classmethod
    def from_file(cls, fp: str) -> list[Self]:
        with open(fp, 'r') as f:
            json_data = json.load(f)

        result = []
        for i, x in enumerate(json_data['results']):
            dt = DATA_TYPE.get_from_char(x['data_type']['formatter_char'])
            if dt is not None:
                endian = ENDIAN.LITTLE_ENDIAN if x['endian'] == 'little' else ENDIAN.BIG_ENDIAN
                elm = cls(x['offset'], x['bytes_step'], dt.data_type_meta_data(), endian, x['quality_index'])
                elm.streak = range(x['streak'][0], x['streak'][1], x['streak'][2] + x['streak'][3])
                result.append(elm)

        return result

    def __init__(self, offset: int, bytes_step: int, data_type: DataTypeMetaData, endian: ENDIAN, quality_index: float):
        self._quality_index = quality_index
        self.offset = offset
        self.bytes_step = bytes_step
        self.data_type = data_type
        self.endian = endian
        self._streak: range = range(offset, offset)
        self._values = []

    @property
    def values(self) -> list:
        return self._values

    @values.setter
    def values(self, values: list):
        self._values = values

    @property
    def streak(self) -> range:
        return self._streak

    @property
    def quality_index(self) -> float:
        return float(self._quality_index)

    @quality_index.setter
    def quality_index(self, value: float):
        self._quality_index = value

    @streak.setter
    def streak(self, value: range):
        self.offset = value.start
        self.bytes_step = value.step - self.data_type.length_in_byte
        self._streak = value

    def streak_summery(self) -> tuple[int, int, int, int]:
        return (self.streak.start, self.streak.stop, self.data_type.length_in_byte, self.bytes_step)

    def __str__(self):
        return f'{self.data_type.formatter_char} ({self.streak.start} -[{self.data_type.length_in_byte} + {self.bytes_step}]- {self.streak.stop}) [{self.quality_index}]'

    def __dict__(self):
        return {
            'offset': self.offset,
            'bytes_step': self.bytes_step,
            'data_type': self.data_type.__dict__(),
            'endian': self.endian.value,
            'quality_index': self.quality_index,
            'streak': self.streak_summery(),
            'values': self._values
        }


class DATA_TYPE(Enum):
    # Priority index, Formatter, big endian, little endian
    DOUBLE = (1, 'd', 8, 0x7FE0000000000000)
    LONG_LONG = (2, 'q', 8, 0xFFFFFFFFFFF00000)
    U_LONG_LONG = (3, 'Q', 8, 0xFFFFFFFFFFF00000)
    FLOAT = (4, 'f', 4, 0x7F000000)
    INT = (5, 'i', 4, 0xFFFF0000)
    U_INT = (6, 'I', 4, 0xFFFF0000)
    SHORT = (7, 'h', 2, 0xFF00)
    U_SHORT = (7, 'H', 2, 0xFF00)
    CHAR = (9, 'b', 1, 0xF0)
    U_CHAR = (10, 'B', 1, 0xF0)

    @classmethod
    def get_from_char(cls, char: str) -> Self:
        for x in cls:
            if x.value[1] == char:
                return x
        return None

    @classmethod
    def prio_list(cls):
        for a in list(cls):
            yield a

    def data_type_meta_data(self) -> DataTypeMetaData:
        return DataTypeMetaData(*self.value)

