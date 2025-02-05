import json
import os

import pytest

from BinaryDataDecoder.data_finder import BinaryDataFinder
from BinaryDataDecoder.extract_data import DataExtractor
from BinaryDataDecoder.helper import FoundDataInfo, DATA_TYPE, ENDIAN
from tests.prepare_test_data import double_v, double_expo_v, double_sqrt_v, short_v, int_v

BIN_PATH = os.path.join(os.path.dirname(__file__), "..", "test_files", "MSPeak.bin")
DDI_BIN_PATH = os.path.join(os.path.dirname(__file__), "..", "test_files", "ddi.bin")

REPORT = os.path.join(os.path.dirname(__file__), "binary_data_decoder", "report.json")
REPORT_SINGLE = os.path.join(os.path.dirname(__file__), "binary_data_decoder", "report_single.json")




def test_validate():
    fi = FoundDataInfo(68, 0, data_type=DATA_TYPE.DOUBLE.data_type_meta_data(), endian=ENDIAN.LITTLE_ENDIAN, quality_index=0)

    filename = BIN_PATH
    BinaryDataFinder(number_of_threads=10, file_path=filename, min_length_data=1000).read()._validate_whole_streak(fi)
    assert fi.streak == range(68, 19668, 8)
    assert int(fi.quality_index) == 114


def test_validation_all():
    fi_list = FoundDataInfo.from_file(REPORT_SINGLE)
    bdf = BinaryDataFinder(number_of_threads=10, file_path=BIN_PATH, min_length_data=500).read()
    total_idx = 0
    for fi in fi_list:
        bdf._validate_whole_streak(fi)
        total_idx += fi.quality_index
    total_idx = total_idx // 1e92
    assert total_idx < 55000000
    assert total_idx > 45000000




def test_overlay():
    fi_list = FoundDataInfo.from_file(REPORT)
    fi_list = BinaryDataFinder(BIN_PATH)._find_overlapping_streaks(fi_list)
    fi_list = BinaryDataFinder(BIN_PATH)._find_overlapping_streaks(fi_list)

    assert len(fi_list) == 267


test_variations = (
        (double_v, "d", None),
        (double_sqrt_v, "sqrt_d", None),
        (double_expo_v, "expo_d", None),
        (short_v, "h", [DATA_TYPE.SHORT]),
        (int_v, "i", [DATA_TYPE.INT]),
)
@pytest.mark.parametrize("config", test_variations)
def test_simple_values(config):
    values, filename, dts = config
    file_path = os.path.join(os.path.dirname(__file__), "..", "test_files", f"{filename}.bin")
    bdf = BinaryDataFinder(file_path, min_length_data=200, number_of_threads=2).read().find_data(data_types=dts)
    res = bdf.results
    assert len(res) == 1
    DataExtractor(bdf).extract_values()
    assert list(res[0].values) == values

@pytest.mark.parametrize("config", test_variations)
def test_simple_values_with_seperator(config):
    values, filename, dts = config
    file_path = os.path.join(os.path.dirname(__file__), "..", "test_files", f"{filename}_sep.bin")
    bdf = BinaryDataFinder(file_path, min_length_data=200, number_of_threads=2).read().find_data(data_types=dts)
    res = bdf.results
    assert len(res) == 1
    DataExtractor(bdf).extract_values()
    assert list(res[0].values) == values



def test_ddi_without_i():

    bdf = BinaryDataFinder(DDI_BIN_PATH, min_length_data=200, number_of_threads=2).read().find_data(data_types=[DATA_TYPE.DOUBLE])
    res = bdf.results
    assert len(res) == 2
    assert res[0].streak == range(0, 9800, 20)
    assert res[1].streak == range(8, 9800, 20)
    DataExtractor(bdf).extract_values()
    assert list(res[0].values) == double_v
    assert list(res[1].values) == double_expo_v




def test_following_d():

    bdf = BinaryDataFinder(DDI_BIN_PATH, min_length_data=200, number_of_threads=2).read().find_data(data_types=[DATA_TYPE.DOUBLE])
    res = bdf.results
    assert len(res) == 2
    assert res[0].streak == range(0, 9800, 20)
    assert res[1].streak == range(8, 9800, 20)
    DataExtractor(bdf).extract_values()
    assert list(res[0].values) == double_v
    assert list(res[1].values) == double_expo_v


def test_ddi():

    bdf = BinaryDataFinder(DDI_BIN_PATH, min_length_data=200, number_of_threads=2).read().find_data(data_types=[DATA_TYPE.DOUBLE, DATA_TYPE.INT])
    res = bdf.results
    assert len(res) == 3
    assert res[0].streak == range(0, 9800, 20)
    assert res[1].streak == range(8, 9800, 20)
    assert res[2].streak == range(16, 9800, 20)
    DataExtractor(bdf).extract_values()
    assert list(res[0].values) == double_v
    assert list(res[1].values) == double_expo_v
    assert list(res[2].values) == int_v
