import os
import struct

double_v = [(x - 25) * 0.1 for x in range(10, 500)]
double_sqrt_v = [(x * 0.1) ** 2 for x in range(10, 500)]
double_expo_v = [2 ** (x * 0.1) for x in range(10, 500)]
short_v = [(x - 250) * 100 for x in range(10, 500)]
int_v = [x * 1000 for x in range(10, 500)]


def open_local(fp, mode):
    fp = os.path.join(os.path.dirname(__file__), fp)
    return open(fp, mode)


def add_byte_seperator(data_list: list, data_type: str, seperator: bytes):
    res = []
    res_type = []

    c = 'c' * len(seperator)
    for data in data_list:
        res.append(data)
        res_type.append(data_type)
        res.append(seperator)
        res_type.append(c)

    return (res[:-1], ''.join(res_type[:-1]))


def write_data_bin_with_and_without_seperator(data_list: list, data_type: str, seperator: bytes = b';',
                                              file_prefix: str = ''):
    if file_prefix != '':
        file_prefix += '_'
    file_prefix += data_type

    write_data_bin(data_list, data_type * len(data_list), file_prefix)
    data_list_seperated, double_seperated_format = add_byte_seperator(data_list, data_type, seperator)
    write_data_bin(data_list_seperated, double_seperated_format, file_prefix, 'sep')


def write_data_bin(data_list: list, data_type: str, file_prefix: str = '', file_suffix: str = ''):
    if file_suffix != '':
        file_suffix = '_' + file_suffix
    byte_data = struct.pack('<' + data_type, *data_list)
    with open_local(f'../test_files/{file_prefix}{file_suffix}.bin', "wb") as f:
        f.write(byte_data)


if __name__ == "__main__":


    write_data_bin_with_and_without_seperator(double_v, 'd')
    write_data_bin_with_and_without_seperator(double_sqrt_v, 'd', file_prefix='sqrt')
    write_data_bin_with_and_without_seperator(double_expo_v, 'd', file_prefix='expo')
    write_data_bin_with_and_without_seperator(short_v, 'h')
    write_data_bin_with_and_without_seperator(int_v, 'i')
    write_data_bin_with_and_without_seperator(double_v + double_sqrt_v, 'd', file_prefix='follow')
    douple_douple_int_v = []
    for i, value in enumerate(double_v):
        douple_douple_int_v.append(value)
        douple_douple_int_v.append(double_expo_v[i])
        douple_douple_int_v.append(int_v[i])

    write_data_bin(douple_douple_int_v, 'ddi' * len(int_v), 'ddi')
