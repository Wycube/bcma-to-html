import struct, math
import PIL.Image


class BCLIM:
    def __init__(self, data: bytes):
        self.data = data
        self.header = self.parse_header()
        self.image = self.parse_image()

    def parse_header(self):
        # Should be last 0x28 bytes
        header_data = self.data[-0x28:]
        
        assert(header_data[:4] == b'CLIM')
        self.endian = '<' if header_data[4:6] == b'\xff\xfe' else '>'

        header_format = self.endian + "IBBII4sIHHII"
        assert(struct.calcsize(header_format) == 0x22)

        header = struct.unpack(header_format, header_data[6:])
        assert(header[5] == b'imag')
        assert(header[4] == 1)

        return header
    
    def parse_image(self):
        assert(self.header[1] == 2 and self.header[2] == 2)

        # TODO: Add etc1 decoding (formats 10 and 11)

        # Round the dimensions to the next power of two then divide by 8 to get the number of tiles
        rounded_w = 1 << int(math.ceil(math.log2(self.header[7]))) >> 3
        rounded_h = 1 << int(math.ceil(math.log2(self.header[8]))) >> 3
        image = bytearray(self.header[7] * self.header[8] * 4)

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
            case 2: # LA4
                pixel = self.data[index]
                rgba = [(pixel >> 4) * 17] * 3
                rgba.append((pixel & 0xF) * 17)
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
                print(f"Unknown format: {self.header[9]}")
                assert(False)
    
    def save_as_png(self, path):
        export = PIL.Image.new("RGBA", (self.header[7], self.header[8]))
        export.frombytes(self.image)
        export.save(path, format="png")