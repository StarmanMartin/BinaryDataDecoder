def open_as_binary(filename, offset, n_bytes):
    split_lines = []
    try:
        with open(filename, 'rb') as f:
            lines = b''.join(f.readlines())[offset:]
            for i in range(0, len(lines), n_bytes):
                split_lines.append(lines[i:i + n_bytes])
    except FileNotFoundError:
        print("File Not Found")
    return split_lines