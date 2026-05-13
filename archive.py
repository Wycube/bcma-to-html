import struct


def decompress_lz10(compressed: bytes):
    # Check for header
    assert(compressed[0] == 0x10)
    # Next 24 bits of header is the decompressed size
    expected_size = compressed[1] | (compressed[2] << 8) | (compressed[3] << 16)

    compressed = compressed[4:]
    decompressed = bytearray()

    # Decompression loop, first byte contains flags about whether the next elements are compressed or not.
    # Uncompressed elements are single bytes copied to the output, compressed elements are a pair of bytes
    # that determine the offset and length to back-reference.
    pointer = 0
    while pointer < len(compressed):
        flags = compressed[pointer]
        pointer += 1

        for i in range(8):
            flag_bit = flags >> (7 - i) & 1

            if pointer >= len(compressed):
                break

            if flag_bit:
                length = (compressed[pointer] >> 4) + 3
                offset = (((compressed[pointer] & 0xF) << 8) | compressed[pointer + 1]) + 1

                # Copy back reference from already decompressed data
                for _ in range(length):
                    decompressed.append(decompressed[-offset])

                pointer += 2
            else:
                decompressed.append(compressed[pointer])
                pointer += 1
    
    assert(len(decompressed) == expected_size)

    return decompressed

class DARC:
    # Indices into header data
    HEADERS_LEN = 0
    VERSION = 1
    FILES_LEN = 2
    FILE_TAB_OFF = 3
    FILE_TAB_LEN = 4
    FILE_DAT_OFF = 5

    def __init__(self, data: bytes):
        self.data = data
        self.endian, self.header = self.parse_header()
        self.file_tree = self.construct_file_tree()
    
    def parse_header(self):
        assert(self.data[:4] == b'darc')
        endian = '<' if self.data[4:6] == b'\xff\xfe' else '>'
        header_format = endian + "HIIIII"
        format_size = struct.calcsize(header_format)
        
        return endian, struct.unpack(header_format, self.data[6:6 + format_size])

    def construct_file_tree(self):
        table_start = self.header[self.FILE_TAB_OFF]
        table_length = self.header[self.FILE_TAB_LEN]
        table_data = self.data[table_start:table_start + table_length]

        # Build the tree structure
        num_entries, file_tree = self.build_file_tree(table_data, 0)
        
        # Get the file/folder names
        self.assign_file_names(table_data[num_entries * 12:], file_tree)

        return file_tree

    def build_file_tree(self, table_data: bytes, index: int):
        folder = []
        info = struct.unpack(self.endian + "III", table_data[index * 12:index * 12 + 12])
        assert(info[0] & 0x01000000)

        index += 1
        end_index = info[2]
        while index < end_index:
            next_info = struct.unpack(self.endian + "III", table_data[index * 12:index * 12 + 12])

            if next_info[0] & 0x01000000:
                # Folder
                index, child = self.build_file_tree(table_data, index)
                folder.append(child)
            else:
                # File
                folder.append([next_info[0], next_info[1], next_info[2]])
                index += 1

        return index, [info[0] & 0xFFFFFF, folder]

    def assign_file_names(self, name_data: bytes, file_tree: list[int, list]):
        offset = file_tree[0]
        term_index = name_data.find(b'\x00\x00', offset)
        name = name_data[offset:term_index + 1].decode("utf-16") if term_index != 0 else ""
        file_tree[0] = name

        for node in file_tree[1]:
            if isinstance(node[1], list):
                # Recurse on folder
                self.assign_file_names(name_data, node)
            else:
                # Get name for file
                offset = node[0]
                term_index = name_data.find(b'\x00\x00', offset)
                name = name_data[offset:term_index + 1].decode("utf-16")
                node[0] = name

    def has_file(self, name: str):
        return self.find_file_impl(name, "", self.file_tree) is not None

    def find_file_impl(self, name: str, pathname: str, folder: list[str, list]):
        for node in folder[1]:
            if isinstance(node[1], list):
                result = self.find_file_impl(name, pathname + node[0] + "/", node)
                if result is not None:
                    return result
            elif pathname + node[0] == name:
                return node[1:]

        return None

    def get_file(self, name: str):
        file_info = self.find_file_impl(name, "", self.file_tree)
        if file_info is None:
            return None
        
        # Get contents from data array using the offset and length provided
        return self.data[file_info[0]:file_info[0] + file_info[1]]
