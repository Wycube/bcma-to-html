import struct, math
import PIL.Image


ETC1_MOD_TABLE = (
    ( 2,   8,  -2,   -8),
    ( 5,  17,  -5,  -17),
    ( 9,  29,  -9,  -29),
    (13,  42, -13,  -42),
    (18,  60, -18,  -60),
    (24,  80, -24,  -80),
    (33, 106, -33, -106),
    (47, 183, -48, -183)
)

def decode_etc1_tile(word: int, alphas: int):
    diff_bit = (word >> 33) & 1 == 1
    flip_bit = (word >> 32) & 1 == 1
    index_bits = []
    for i in range(16):
        index_bits.append(((word >> i) & 1) | ((word >> (15 + i)) & 2))

    table_code_1 = (word >> 37) & 7
    table_code_2 = (word >> 34) & 7
    base_color_1 = None
    base_color_2 = None
    if diff_bit:
        base_r = (word >> 59) & 0x1F
        base_g = (word >> 51) & 0x1F
        base_b = (word >> 43) & 0x1F

        # 3-bit two's complement
        delta_r = base_r + ((word >> 58) & 1) * -4 + ((word >> 56) & 3)
        delta_g = base_g + ((word >> 50) & 1) * -4 + ((word >> 48) & 3)
        delta_b = base_b + ((word >> 42) & 1) * -4 + ((word >> 40) & 3)
        assert delta_r < 32 and delta_r >= 0, "red overflowed/underflowod ({}, {})".format(base_r, delta_r)
        assert delta_g < 32 and delta_g >= 0, "green overflowed/underflowed ({}, {})".format(base_g, delta_g)
        assert delta_b < 32 and delta_b >= 0, "blue overflowed/underflowed ({}, {})".format(base_b, delta_b)

        base_color_1 = ((base_r << 3) | (base_r >> 2), (base_g << 3) | (base_g >> 2), (base_b << 3) | (base_b >> 2))
        base_color_2 = ((delta_r << 3) | (delta_r >> 2), (delta_g << 3) | (delta_g >> 2), (delta_b << 3) | (delta_b >> 2))
    else:
        base_r_1 = (word >> 60) & 0xF
        base_g_1 = (word >> 52) & 0xF
        base_b_1 = (word >> 44) & 0xF
        base_r_2 = (word >> 56) & 0xF
        base_g_2 = (word >> 48) & 0xF
        base_b_2 = (word >> 40) & 0xF
        base_color_1 = ((base_r_1 << 4) | base_r_1, (base_g_1 << 4) | base_g_1, (base_b_1 << 4) | base_b_1)
        base_color_2 = ((base_r_2 << 4) | base_r_2, (base_g_2 << 4) | base_g_2, (base_b_2 << 4) | base_b_2)
    
    tile = bytearray(4 * 4 * 4)
    for i in range(16):
        x = i // 4
        y = i % 4
        color = base_color_1 if (x < 2 and not flip_bit) or (y < 2 and flip_bit) else base_color_2
        table = table_code_1 if (x < 2 and not flip_bit) or (y < 2 and flip_bit) else table_code_2
        mod_table = ETC1_MOD_TABLE[table]
        index = index_bits[i]
        tile[i * 4 + 0] = min(255, max(0, color[0] + mod_table[index]))
        tile[i * 4 + 1] = min(255, max(0, color[1] + mod_table[index]))
        tile[i * 4 + 2] = min(255, max(0, color[2] + mod_table[index]))
        
        alpha = (alphas >> i * 4) & 0xF
        tile[i * 4 + 3] = (alpha << 4) | alpha
    
    return tile

def copy_tile(buffer, start, width, tile):
    for i in range(16):
        tile_x = i // 4
        tile_y = i % 4
        offset = start + (tile_x + tile_y * width * 4) * 4
        buffer[offset + 0] = tile[i * 4 + 0]
        buffer[offset + 1] = tile[i * 4 + 1]
        buffer[offset + 2] = tile[i * 4 + 2]
        buffer[offset + 3] = tile[i * 4 + 3]

def decode_etc1(data: bytes, tiles: tuple[int, int], alpha: bool = False):
    # Loop through all tiles and decode
    decoded = bytearray(tiles[0] * tiles[1] * 16 * 4)    
    for i in range(tiles[0] * tiles[1]):
        z_tile_pos = i % 4
        z_tile_num = i // 4

        # Deswizzle the morton tiling (4x4)
        x = z_tile_pos & 1
        y = z_tile_pos >> 1
        x += z_tile_num % (tiles[0] // 2) * 2
        y += z_tile_num // (tiles[0] // 2) * 2

        tile_data = None
        tile_alphas = None
        if alpha:
            tile_alphas, tile_data = struct.unpack("<QQ", data[i * 16:(i + 1) * 16])
        else:
            tile_alphas = ~0
            tile_data = struct.unpack("<Q", data[i * 8:(i + 1) * 8])[0]


        etc1_tile = decode_etc1_tile(tile_data, tile_alphas)
        start = (x * 4 + y * 4 * tiles[0] * 4) * 4
        copy_tile(decoded, start, tiles[0], etc1_tile)
    
    return decoded

class BCLIM:
    def __init__(self, data: bytes):
        self.data = data
        self.header = self.parse_header()
        self.image = self.parse_image()

    def parse_header(self):
        # Should be last 0x28 bytes
        header_data = self.data[-0x28:]
        
        assert header_data[:4] == b'CLIM'
        self.endian = '<' if header_data[4:6] == b'\xff\xfe' else '>'

        header_format = self.endian + "IBBII4sIHHII"
        assert struct.calcsize(header_format) == 0x22

        header = struct.unpack(header_format, header_data[6:])
        assert header[5] == b'imag'
        assert header[4] == 1

        return header
    
    def parse_image(self):
        assert self.header[1] == 2 and self.header[2] == 2
        assert self.header[9] in (2, 3, 5, 6, 7, 8, 9, 10, 11), "Unknown format {}!".format(self.header[9])

        # Round the dimensions to the next power of two then divide by 8 to get the number of tiles
        rounded_w = 1 << int(math.ceil(math.log2(self.header[7]))) >> 3
        rounded_h = 1 << int(math.ceil(math.log2(self.header[8]))) >> 3
        image = bytearray(self.header[7] * self.header[8] * 4)
        
        # ETC1 and ETC1A4 decoding
        if self.header[9] in (10, 11):
            etc1 = decode_etc1(self.data, (rounded_w << 1, rounded_h << 1), self.header[9] == 11)
            for x in range(self.header[7]):
                for y in range(self.header[8]):
                    image[(x + y * self.header[7]) * 4 + 0] = etc1[(x + y * (rounded_w * 8)) * 4 + 0]
                    image[(x + y * self.header[7]) * 4 + 1] = etc1[(x + y * (rounded_w * 8)) * 4 + 1]
                    image[(x + y * self.header[7]) * 4 + 2] = etc1[(x + y * (rounded_w * 8)) * 4 + 2]
                    image[(x + y * self.header[7]) * 4 + 3] = etc1[(x + y * (rounded_w * 8)) * 4 + 3]
            
            return image

        for i in range(rounded_w * rounded_h * 64):
            tile_pos = i % 64
            tile_num = i // 64

            # Deswizzle the morton tiling
            x = 0
            y = 0
            for j in range(3):
                x |= ((tile_pos >> (j * 2)) & 1) << j
                y |= ((tile_pos >> (j * 2 + 1)) & 1) << j
            
            x += tile_num % rounded_w * 8
            y += tile_num // rounded_w * 8

            # Don't try to add pixels outside of the image range
            if x >= self.header[7] or y >= self.header[8]:
                continue

            pixel = self.decode_pixel(i)
            image[(x + y * self.header[7]) * 4 + 0] = pixel[0]
            image[(x + y * self.header[7]) * 4 + 1] = pixel[1]
            image[(x + y * self.header[7]) * 4 + 2] = pixel[2]
            image[(x + y * self.header[7]) * 4 + 3] = pixel[3]
        
        return image

    def decode_pixel(self, index):
        match self.header[9]:
            case 2: # LA44
                pixel = self.data[index]
                rgba = [(pixel >> 4) * 17] * 3
                rgba.append((pixel & 0xF) * 17)
                return rgba
            case 3: # LA88
                lum = self.data[index * 2]
                alpha = self.data[index * 2 + 1]
                rgba = [lum] * 3
                rgba.append(alpha)
                return rgba
            case 5: # RGB565
                pixel = self.data[index * 2] | (self.data[index * 2 + 1] << 8)
                rgba = [int((pixel >> 11) * (255 / 31)), int(((pixel >> 5) & 0x3F) * (255 / 63)), int((pixel & 0x1F) * (255 / 31))]
                rgba.append(255)
                return rgba
            case 6: # RGB888
                rgba = [self.data[index * 3 + (2 - i)] for i in range(3)]
                rgba.append(255)
                return rgba
            case 7: # RGBA5551
                pixel = self.data[index * 2] | (self.data[index * 2 + 1] << 8)
                rgba = [int(((pixel >> ((2 - i) * 5 + 1)) & 0x1F) * (255 / 31)) for i in range(3)]
                rgba.append(255 * (pixel & 1))
                return rgba
            case 8: # RGBA4444
                pixel = self.data[index * 2] | (self.data[index * 2 + 1] << 8)
                return [((pixel >> (3 - i) * 4) & 0xF) * 17 for i in range(4)]
            case 9: # RGBA8888
                return [self.data[index * 4 + (3 - i)] for i in range(4)]
            case _:
                return [0, 0, 0, 0]
    
    def save_as_png(self, path):
        export = PIL.Image.new("RGBA", (self.header[7], self.header[8]))
        export.frombytes(self.image)
        export.save(path, format="png")