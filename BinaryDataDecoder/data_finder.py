import json
import math
import os.path
import struct
import threading
import time
import warnings
from collections.abc import Sequence
from typing import Self

import numpy as np

from BinaryDataDecoder.helper import FoundDataInfo, DATA_TYPE, ENDIAN, DataTypeMetaData
from BinaryDataDecoder.utils import open_as_binary_lines, RESULT_DIR

warnings.filterwarnings('ignore')

class BinaryDataFinder():
    MAX_VALUE = 1e100
    THRESHOLD_COMPARE_BITS = 3
    MAX_VALIDATION_ERROR = 1000

    def __init__(self, file_path: str, min_length_data: int = 1000,
                 number_of_threads: int = 5, value_in_row: int=2):
        self._is_running = True
        self._pre_refined_results = []
        self._fp = file_path
        self._file_handler = None
        self._number_of_threads = number_of_threads
        self._min_length_data = min_length_data
        self._lock = threading.RLock()
        self._chunk_idx = 0
        self._chunks = None
        chunk_size = min_length_data * 5
        self._test_chunk_size = chunk_size
        self._chunk_size = 0
        self._total_size = 0
        self._offset = 0
        self._results: list[FoundDataInfo] = []
        self._value_in_row = value_in_row * 8 + 1

    def __del__(self):
        if self._file_handler is not None:
            self._file_handler.close()

    @property
    def results(self):
        return self._results

    def read(self) -> Self:
        self._number_of_threads += 1

        while self._chunk_size < self._test_chunk_size:
            self._number_of_threads = max(1, self._number_of_threads - 1)

            self._chunks = open_as_binary_lines(self._fp, 0, n_parts=self._number_of_threads)
            self._total_size = sum(len(chunk) for chunk in self._chunks)
            self._chunk_size = len(self._chunks[0])

            if self._number_of_threads == 1:
                self._test_chunk_size = min(self._chunk_size, self._test_chunk_size)
                return self

        return self

    def load_result(self, fp: str)-> Self:
        self._results = FoundDataInfo.from_file(fp)
        return self

    def write_results_to_file(self, out_path: str = None) -> str:
        if out_path is None:
            out_path = os.path.join(RESULT_DIR, 'report.json')

        with open(out_path, 'w') as report:
            report_obj = {'results': [x.__dict__() for x in self._results]}
            report.write(json.dumps(report_obj, indent=4))

        return os.path.abspath(out_path)

    def find_data(self, data_types: list[DATA_TYPE] | None = None, endian: ENDIAN | None = None) -> Self:
        if self._chunks is None:
            self.read()

        if data_types is None:
            data_types = DATA_TYPE.prio_list()
        elif isinstance(data_types, DATA_TYPE):
            data_types = [data_types]

        data_types = [d.data_type_meta_data() for d in data_types]
        total_steps = self._chunk_size // self._test_chunk_size
        step = 0
        time_in_s = 0
        self._offset = 0
        print(f"Starting... # collecting data in of Steps: {total_steps}", end='', flush=True)
        while True:
            step += 1
            self._chunk_idx = 0

            if self._chunk_size - self._offset < self._test_chunk_size:
                self._results.sort(key=lambda a: a.offset)
                self._results = self._find_overlapping_streaks(self._results)
                self._results = self._find_overlapping_streaks(self._results)
                for res in self._results:
                    res.streak = range(res.streak.start, min(self._total_size, res.streak.stop), res.streak.step)
                return self
            start = time.time()

            threads = []
            self._chunk_idx = 0
            for i in range(self._number_of_threads):
                t = threading.Thread(target=self._find_pattern, args=(data_types, endian))
                t.daemon = True
                t.start()
                threads.append(t)

            for t in threads:
                t.join(5000)

            self._offset += self._test_chunk_size
            end = time.time()
            print("\r" + " " * 30, end='', flush=True)
            time_step_in_s =  end - start
            time_in_s += time_step_in_s
            print(f"\rStep: [{step}/{total_steps}] - Time (s): {time_in_s:.3f} ({time_step_in_s:.3f})", end='', flush=True)

    def get_element_at_pos(self, offset: int, data_type: DataTypeMetaData) -> bytes:
        chunk_idx = offset // self._chunk_size
        if chunk_idx >= len(self._chunks):
            raise IndexError("Index out of range")
        idx = offset % self._chunk_size
        chunk = b''.join(self._chunks[chunk_idx:chunk_idx+2])
        if idx + data_type.length_in_byte > len(chunk):
            raise IndexError("Index out of range")
        return chunk[idx:idx + data_type.length_in_byte]

    @staticmethod
    def _split_bytes(data: bytes, n: None | int = None, sep: int = 0):
        if n is None:
            return data
        return [data[i:i + n] for i in range(0, len(data), n + sep) if len(data[i:i + n]) == n]

    @staticmethod
    def _shift_bytes(to_test, max_val):
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

    def _find_overlapping_streaks(self, results: list[FoundDataInfo]) -> list[FoundDataInfo]:
        remove_idx = set()
        results.sort(key=lambda a: a.offset)
        # print(f"\nValidating overlapping streaks... ")
        # print(" " * 30, end='', flush=True)
        for i_a, res_a in enumerate(results[:-1]):
            if i_a in remove_idx:
                continue
            # print("\r" + " " * 30, end='', flush=True)
            # print(f'Validating {i_a}/{len(results)}', end='', flush=True)
            for i_b, res_b in enumerate(results[i_a + 1:]):
                i_b += i_a + 1
                if i_b in remove_idx:
                    continue

                word_a_idx = 0
                found_remove_idx = False
                if res_a.streak.stop < res_b.streak.start:
                    break
                for word_b_start in res_b.streak:
                    for _word_a_idx, word_a_start in enumerate(res_a.streak[word_a_idx:]):
                        word_a_end = word_a_start + res_a.data_type.length_in_byte
                        if word_a_end > word_b_start:
                            word_b_end = word_b_start + res_b.data_type.length_in_byte
                            if word_a_start == word_b_start and word_a_end == word_b_end and max(res_a.streak.step,
                                                                                                 res_b.streak.step) % min(
                                res_a.streak.step, res_b.streak.step) == 0:
                                remove_idx.add(i_b)
                                found_remove_idx = True
                                res_a.streak = range(res_a.streak.start, max(res_a.streak.stop, res_b.streak.stop),
                                                     min(res_a.streak.step, res_b.streak.step))

                            elif word_a_start < word_b_end:
                                remove_idx.add(i_b if res_b.quality_index > res_a.quality_index else i_a)
                                found_remove_idx = True
                            word_a_idx = _word_a_idx
                            break
                    if found_remove_idx:
                        break
        results = [v for i, v in enumerate(results) if i not in remove_idx]
        results.sort(key=lambda a: a.offset)
        return results

    def _move_to_next_vals_in_streak(self, finding: FoundDataInfo, backward: bool = False):
        start_pos = finding.offset
        try:
            chunk_to_test = self.get_element_at_pos(start_pos, finding.data_type)
        except IndexError:
            return start_pos
        last_val = finding.data_type.parse_byte_stream_test_seq(chunk_to_test=chunk_to_test, endian=finding.endian)
        factor = -1 if backward else 1
        next_step = factor * (finding.bytes_step + finding.data_type.length_in_byte)
        while True:
            new_pos = start_pos + next_step
            if new_pos < 0:
                return start_pos
            try:
                chunk_to_test = self.get_element_at_pos(new_pos, finding.data_type)
            except IndexError:
                return start_pos if backward else new_pos
            new_val = finding.data_type.parse_byte_stream_test_seq(chunk_to_test=chunk_to_test, endian=finding.endian)

            compare_value = abs(new_val - last_val)
            if finding.data_type.is_signed_integer:
                compare_value %= finding.data_type.bitmask
            if finding.data_type.formatter_char in ['d', 'f'] and (new_val == 0 or last_val == 0):
                compare_value = abs(compare_value - finding.data_type.bitmask // 2)
            if compare_value >= self.THRESHOLD_COMPARE_BITS:
                return start_pos if backward else new_pos
            last_val = new_val
            start_pos = new_pos

    def _validate_whole_streak(self, finding: FoundDataInfo):
        start_pos = self._move_to_next_vals_in_streak(finding=finding, backward=True)
        end_pos = self._move_to_next_vals_in_streak(finding=finding)
        chunk_positions = range(start_pos, end_pos, finding.bytes_step + finding.data_type.length_in_byte)

        chunks_set = []
        validation_error = 0
        validation_steps = 0
        for pos in chunk_positions:
            chunks_set.append(self.get_element_at_pos(pos, finding.data_type))
            if len(chunks_set) % 4 == 0:
                chunks_set = chunks_set[-5:]
                vr = self._validate_result(b''.join(chunks_set), finding.endian, finding.data_type)
                validation_error += vr

                validation_steps += 1
        if validation_steps == 0:
            finding.quality_index = self.MAX_VALUE
        else:
            finding.quality_index = validation_error / validation_steps / len(
                chunk_positions) * finding.data_type.length_in_byte
            finding.quality_index += 20 * finding.data_type.priority_index
            finding.quality_index += 100 - (
                    500 * len(chunk_positions) * finding.data_type.length_in_byte / self._total_size)
        finding.streak = range(start_pos, end_pos, finding.bytes_step + finding.data_type.length_in_byte)

    def _next_chunk(self):
        with self._lock:
            if self._chunk_idx < len(self._chunks):
                idx = self._chunk_idx
                self._chunk_idx += 1
                return (self._chunks[idx], idx)
            else:
                return None

    def _find_pattern(self, data_types: list[DataTypeMetaData], endian_filter: None | ENDIAN):

        while chunk_and_idx := self._next_chunk():
            chunk, chunk_idx = chunk_and_idx
            chunk = chunk[self._offset:self._offset + 500]
            for data_type in data_types:
                self._find_pattern_in_chunk(chunk, chunk_idx, data_type)

    def _find_pattern_in_chunk(self, chunk: bytes, chunk_idx: int, data_type: DataTypeMetaData):
        result = []
        start_pos = self._chunk_size * chunk_idx + self._offset
        for byte_shift in range(self._value_in_row):
            for (parser, endian) in data_type.endian_bitmasks:
                for step in range(0, self._value_in_row + 8):
                    chunks_to_test = self._split_bytes(chunk[byte_shift:], data_type.length_in_byte, step)[:5]
                    if len(chunks_to_test) < 3:
                        break
                    step_check = all(
                        [x < self.THRESHOLD_COMPARE_BITS for x in
                         self._get_diff([parser(chunk_word) for chunk_word in chunks_to_test], True)])

                    if step_check:
                        quality_index = self._validate_result(b''.join(chunks_to_test), endian, data_type)
                        if quality_index <= self.MAX_VALIDATION_ERROR:
                            result.append(
                                FoundDataInfo(start_pos + byte_shift, step, data_type,
                                              endian, quality_index))
        if len(result):
            self._results_append(result)

    @staticmethod
    def _get_diff(values: Sequence[float], result_abs: bool = False) -> list[float]:
        if result_abs:
            return [abs(values[i + 1] - values[i]) for i in range(len(values) - 1)]
        return [values[i + 1] - values[i] for i in range(len(values) - 1)]

    def _validate_result(self, chunk, endian: ENDIAN, data_type: DataTypeMetaData):
        number_of_results = int(len(chunk) // data_type.length_in_byte)
        if number_of_results < 4:
            return 0
        endian_char = '>' if endian == ENDIAN.BIG_ENDIAN else '<'
        y = struct.unpack(f'{endian_char}{number_of_results}{data_type.formatter_char}', chunk)
        x = list(range(1, len(y) + 1))  # Assume x is just indices
        try:
            # Fit a polynomial of degree 2 (quadratic)
            y = np.array(y, dtype=np.float64)
            if (y < 0).any():
                y = y + y.min() * -1.1
            y /= y.max() / 100
            log_y = np.log(y)
            coeffs = np.polyfit(x, y, 2)
            # Generate predicted values
            y_pred = np.polyval(coeffs, x)
            # Check how well it fits
            error = np.mean((y - y_pred) ** 2)

            coeffs_log = np.polyfit(x, log_y, 1)
            if np.isnan(coeffs_log).any():
                error_log = self.MAX_VALUE
            else:
                # Generate predicted values for exponential
                y_log_pred = np.polyval(coeffs_log, x)
                error_log = np.mean((log_y - y_log_pred) ** 2)
            if math.isinf(error):
                error = self.MAX_VALUE
            return max(0, min(error_log, error))
        except RuntimeWarning:
            return self.MAX_VALUE

    def _results_append(self, params: list[FoundDataInfo]):
        params.sort(key=lambda param: (param.offset, -(param.bytes_step+1)*param.quality_index))
        offsets = [param.offset for param in params]

        params = [x for i, x in enumerate(params) if x.offset not in offsets[i+1:]]

        for param in params:
            self._validate_whole_streak(param)

        params = list(filter(lambda x: x.quality_index < self.MAX_VALIDATION_ERROR, params))
        params = self._find_overlapping_streaks(params)
        for param in params:
            with self._lock:
                added = False
                for res_idx, res in enumerate(self._results):
                    if res.offset == param.offset:
                        if param.quality_index < res.quality_index:
                            self._results[res_idx] = param
                        added = True
                if not added:
                    self._results.append(param)
