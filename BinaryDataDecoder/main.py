import threading
from enum import Enum
from typing import Self


class DataTypeMetaData:
    def __init__(self, priority_index: int, formatter_char: str, big_endian_bitmask: int, little_endian_bitmask: int):
        self.priority_index = priority_index
        self.formatter_char = formatter_char
        self.big_endian_bitmask = big_endian_bitmask
        self.little_endian_bitmask = little_endian_bitmask

class ENDIAN(Enum):
    BIG_ENDIAN = 0
    SMALL_ENDIAN = 1
    UNKNOWN = 2



class DATA_TYPE(Enum):
    # Priority index, Formatter, big endian, little endian
    DOUBLE        = (0, 'd', 8, 0x7FF0000000000000, 0x0000000000000FFE)
    FLOAT         = (1, 'f', 4, 0x7F800000, 0x000001FE)
    LONG_LONG     = (2, 'q', 8, 0xFFFFFFFF00000000, 0x00000000FFFFFFFF)
    U_LONG_LONG   = (3, 'Q', 8 ,0xFFFFFFFFF00000000, 0x00000000FFFFFFFFF)
    INT           = (4, 'i', 4, 0xFFFF0000, 0x0000FFFF)
    U_INT         = (5, 'I', 4, 0xFFF0000, 0x0000FFFF)
    SHORT         = (6, 'q', 2, 0xFF00, 0x00FF)
    U_SHOR_SHORT  = (7, 'Q', 2, 0xFF00, 0x00FF)
    CHAR          = (8, 'b', 1, 0xF0, 0x0F)
    U_CHAR        = (9, 'B', 1, 0xF0, 0x0F)


    def data_type_meta_data(self) -> DataTypeMetaData:
        return DataTypeMetaData(*super().value())

class BinaryDataFinder():

    def __init__(self, file_path: str = None, number_of_threads: int = 5):
        self._fp = file_path
        self._file_handler = None
        self._number_of_threads =number_of_threads
        self._lock = threading.RLock()
        self._chunk_idx = 0
        self._chunks = None

    def __del__(self):
        if self._file_handler is not None:
            self._file_handler.cloas()

    def read(self, file_path: str = None) -> Self:
        if file_path is not None:
            self._fp = file_path
        if self._file_handler is None:
            self._file_handler = open(self._fp, 'rb')
        else:
            raise IOError('File IO handler already open!')

        return self

    def find_data(self, data_type: DATA_TYPE = DATA_TYPE.DOUBLE, endian: ENDIAN = ENDIAN.UNKNOWN,
                  chunk_size: int = 2 ** 13):
        self._file_handler.seek(0)
        self._chunk_idx = 0
        self._chunks = []
        chunk = b''
        while True:
            c = self._file_handler.read(1)
            if not c:
                print("End of file")
                break
            chunk += c
            if len(chunk) == chunk_size:
                self._chunks.append(chunk)
                chunk = b''

            print("Read a character:", c)

    def _next_chunk(self):
        with self._lock:
            idx = self._chunk_idx
            self._chunk_idx += 1
            if idx < len(self._chunks):
                return self._chunks[self._chunk_idx]
            else:
                return None

    @classmethod
    def _get_steps(cls, data_type: DATA_TYPE):
        pass

    def _find_pattern(self, data_type: DATA_TYPE, endian: ENDIAN):
        pass
