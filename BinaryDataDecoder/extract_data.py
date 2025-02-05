import json
import os
import struct
from typing import Self

from BinaryDataDecoder.data_finder import BinaryDataFinder
from BinaryDataDecoder.helper import ENDIAN
from BinaryDataDecoder.utils import RESULT_DIR


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
            report_obj = {'results': [x.__dict__() for x in self._results]}
            report.write(json.dumps(report_obj, indent=4))

    def extract_values(self) -> Self:
        self._results = self._bdf.read().results
        for res in self._results:
            values_as_byts = b''
            for i in res.streak:
                values_as_byts += self._bdf.get_element_at_pos(i, res.data_type)
            data_type = res.data_type
            endian_char = '>' if res.endian == ENDIAN.BIG_ENDIAN else '<'
            number_of_results = len(res.streak)
            res.values = struct.unpack(f'{endian_char}{number_of_results}{data_type.formatter_char}', values_as_byts)
        return self


if __name__ == '__main__':
    dataExtractor = DataExtractor(BinaryDataFinder("/home/martin/PycharmProjects/BinaryDataDecoder/test_files/MSPeak.bin").load_result("/home/martin/PycharmProjects/BinaryDataDecoder/binary_data_decoder/report_ms_bin.json"))
    dataExtractor.extract_values().write_output()
