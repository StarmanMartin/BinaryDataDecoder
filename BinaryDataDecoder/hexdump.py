import json
import os

from BinaryDataDecoder.utils import open_as_binary_lines


class Hexdump:
    @staticmethod
    def _open_as_binary(filename, offset, n_bytes):
        return open_as_binary_lines(filename, offset, n_bytes)

    # encode bytes to hex
    @staticmethod
    def _encode_hex(byte_block):
        hex_ = []
        for x in byte_block:
            hex_.append(f"{x:02x}")
        hex_ = list(zip(hex_[::2], hex_[1::2]))
        bytes_to_hex = ""
        for x in hex_:
            bytes_to_hex += f"{x[0]}{x[1]} "
        return bytes_to_hex

    # decode btye to string
    @staticmethod
    def _decode_bytes(data):
        str_from_hex = ""
        for x in data:
            if x > 31 and x < 127:
                str_from_hex += chr(x)
            else:
                str_from_hex += "."
        return str_from_hex

    @classmethod
    def run(cls, filename: str, offset: int=0, n_bytes: int=16, output_filename: str = 'output.txt'):
        lines = cls._open_as_binary(filename, offset, n_bytes)
        cls.run_from_lines(lines, output_filename, offset)

    @classmethod
    def run_from_lines(cls, lines: list[bytes], output_filename: str = 'output.txt', offset: int = 0):
        if os.path.exists(output_filename):
            os.remove(output_filename)
        with open(output_filename, 'w+') as f:
            for index, line in enumerate(lines):
                f.write(f"{(index * len(line) + offset):08x} {cls._encode_hex(line)} : {cls._decode_bytes(line)}\n")