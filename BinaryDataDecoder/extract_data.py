import json
import os
import struct
from typing import Self

from BinaryDataDecoder.data_finder import BinaryDataFinder
from BinaryDataDecoder.helper import ENDIAN
from BinaryDataDecoder.utils import RESULT_DIR, find_unused_2byte_pair


class DataExtractor:
    def __init__(self, bdf: BinaryDataFinder):
        self._bdf = bdf

    @property
    def results(self) -> list:
        return self._bdf.read().results

    def write_output(self, out_path: str = None):
        if out_path is None:
            out_path = os.path.join(RESULT_DIR, 'report_with_values.json')

        with open(out_path, 'w') as report:
            report_obj = {'results': [x.__dict__() for x in self.results]}
            report.write(json.dumps(report_obj, indent=4))
            
    def write_bin_leftovers(self, out_path: str = None) -> str:
        if out_path is None:
            fn = os.path.basename(self._bdf.fp) + '_leftovers.bin'
            out_path = os.path.join(RESULT_DIR, fn)

        with open(out_path, 'wb+') as report:
            content_chunks = self._bdf.bin_file_contents
            offset = 0
            for content in content_chunks:
                replacement = find_unused_2byte_pair(content)
                content_array = bytearray(content)
                for res in self.results:
                    for i in res.streak:
                        start = i - offset
                        end = start+res.data_type.length_in_byte
                        if end >= 0 and start < len(content_array):
                            start = max(0, start)
                            content_array[start:end] = replacement * int(res.data_type.length_in_byte // 2)
                offset += len(content_array)
                content_array = content_array.replace(replacement, b'')
                report.write(content_array)

        return os.path.abspath(out_path)





    def extract_values(self) -> Self:
        for res in self.results:
            values_as_byts = b''
            for i in res.streak:
                values_as_byts += self._bdf.get_element_at_pos(i, res.data_type)
            data_type = res.data_type
            endian_char = '>' if res.endian == ENDIAN.BIG_ENDIAN else '<'
            number_of_results = len(res.streak)
            res.values = struct.unpack(f'{endian_char}{number_of_results}{data_type.formatter_char}', values_as_byts)
        return self
