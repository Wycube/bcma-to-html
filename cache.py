import os
import archive, texture
import PIL


class TextureCache:
    def __init__(self, archives: list[archive.DARC], export_dir: str):
        self.archives = archives
        self.export_dir = export_dir
        self.cached_textures: list[str] = []
        self.cached_borders: list[tuple[list[tuple[str, int]], tuple[int, int], str, list[int]]] = []

    def find(self, name: str):
        for darc in self.archives:
            if darc.has_file("./timg/" + name):
                return texture.BCLIM.get_size(darc.get_file("./timg/" + name))

        return None

    def cache(self, name: str):
        size = self.find(name)
        if size is not None and name not in self.cached_textures:
            self.cached_textures.append(name)

    def find_border(self, frames: list[tuple[str, int]]):
        for border in self.cached_borders:
            if border[0] == frames:
                return border[1:]

        return None

    def cache_border(self, frames: list[tuple[str, int]]):
        info =  self.find_border(frames)
        if info is not None:
            return info

        # Create nine-patch image and add to cache
        corners: list[tuple[texture.BCLIM, bool, bool]] = []
        for frame in frames:
            name = frame[0]
            for darc in self.archives:
                if darc.has_file("./timg/" + name):
                    bclim = texture.BCLIM(darc.get_file("./timg/" + name))
                    
                    # TODO: Handle all flip types
                    assert frame[1] in (0, 1, 2, 4), f"Flip type {frame[1]} unimplemented!"
                    corners.append((bclim, frame[1] in (1, 4), frame[1] in (2, 4)))
                    break

        border_image_size = (0, 0)
        border_image = None

        if len(corners) == 0:
            return
        elif len(corners) == 1:
            corners.append((corners[0][0], True, False))
            corners.append((corners[0][0], False, True))
            corners.append((corners[0][0], True, True))

        # Make sure corner dimensions match
        # TODO: Figure out what happens if they don't
        assert(corners[0][0].header[7] == corners[2][0].header[7])
        assert(corners[1][0].header[7] == corners[3][0].header[7])
        assert(corners[0][0].header[8] == corners[1][0].header[8])
        assert(corners[2][0].header[8] == corners[3][0].header[8])
        border_image_size = (corners[0][0].header[7] + 1 + corners[1][0].header[7], corners[2][0].header[8] + 1 + corners[1][0].header[8])
        border_image = [0 for _ in range(border_image_size[0] * border_image_size[1] * 4)]

        for i, corner in enumerate(corners):
            # Copy image to specific spot
            start_x = 0 if i % 2 == 0 else corners[0][0].header[7] + 1
            start_y = 0 if i // 2 == 0 else corners[0][0].header[8] + 1

            for x in range(corner[0].header[7]):
                for y in range(corner[0].header[8]):
                    src_x = (corner[0].header[7] - 1 - x) if corner[1] else x
                    src_y = (corner[0].header[8] - 1 - y) if corner[2] else y
                    border_image[(start_x + x + (start_y + y) * border_image_size[0]) * 4 + 0] = corner[0].image[(src_x + src_y * corner[0].header[7]) * 4 + 0]
                    border_image[(start_x + x + (start_y + y) * border_image_size[0]) * 4 + 1] = corner[0].image[(src_x + src_y * corner[0].header[7]) * 4 + 1]
                    border_image[(start_x + x + (start_y + y) * border_image_size[0]) * 4 + 2] = corner[0].image[(src_x + src_y * corner[0].header[7]) * 4 + 2]
                    border_image[(start_x + x + (start_y + y) * border_image_size[0]) * 4 + 3] = corner[0].image[(src_x + src_y * corner[0].header[7]) * 4 + 3]

            # Copy last edge to next row/column for sides
            start_x1 = [corners[0][0].header[7] - 1, corners[0][0].header[7] + 1, 0, corners[0][0].header[7] + 1][i]
            start_x2 = [corners[0][0].header[7], corners[0][0].header[7] + 1, 0, corners[0][0].header[7]][i]
            start_y1 = [0, corners[0][0].header[8] - 1, corners[0][0].header[8] + 1, corners[0][0].header[8] + 1][i]
            start_y2 = [0, corners[0][0].header[8], corners[0][0].header[8], corners[0][0].header[8] + 1][i]
            direction = [(0, 1), (1, 0), (1, 0), (0, 1)][i]
            size = [corners[0][0].header[8], corners[0][0].header[7], corners[0][0].header[7], corners[0][0].header[8]][i]

            for i in range(size):
                x1 = start_x1 + direction[0] * i
                y1 = start_y1 + direction[1] * i
                x2 = start_x2 + direction[0] * i
                y2 = start_y2 + direction[1] * i
                border_image[(x2 + y2 * border_image_size[0]) * 4 + 0] = border_image[(x1 + y1 * border_image_size[0]) * 4 + 0]
                border_image[(x2 + y2 * border_image_size[0]) * 4 + 1] = border_image[(x1 + y1 * border_image_size[0]) * 4 + 1]
                border_image[(x2 + y2 * border_image_size[0]) * 4 + 2] = border_image[(x1 + y1 * border_image_size[0]) * 4 + 2]
                border_image[(x2 + y2 * border_image_size[0]) * 4 + 3] = border_image[(x1 + y1 * border_image_size[0]) * 4 + 3]

        # Create unique name for it.
        # TODO: Right now it is border_*, but that could potentially clash with other texture names
        border_name = f"border_{len(self.cached_borders)}"
        self.cached_borders.append((frames, border_image_size, border_name, border_image))

        return self.cached_borders[-1][1:]

    def export(self):
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)

        for name in self.cached_textures:
            for darc in self.archives:
                if darc.has_file("./timg/" + name):
                    bclim = texture.BCLIM(darc.get_file("./timg/" + name))
                    bclim.save_as_png(self.export_dir + name.replace(".bclim", ".png"))

        for entry in self.cached_borders:
            export = PIL.Image.new("RGBA", entry[1])
            export.frombytes(bytes(entry[3]))
            export.save(self.export_dir + entry[2] + ".png", format="png")