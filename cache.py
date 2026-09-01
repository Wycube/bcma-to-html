import os
import archive, texture

# TODO: Also cache window border images and associated parameters so they can be reused instead of making/exporting the same image multiple times


class TextureCache:
    def __init__(self, archives, export_dir):
        self.archives = archives
        self.export_dir = export_dir
        self.cached_textures = []
        self.cached_borders = []

    def find(self, name):
        for darc in self.archives:
            if darc.has_file("./timg/" + name):
                return texture.BCLIM.get_size(darc.get_file("./timg/" + name))

        return None

    def cache(self, name):
        size = self.find(name)
        if size is not None and name not in self.cached_textures:
            self.cached_textures.append(name)

    def find_border_texture(self, frames):
        for border in self.cached_borders:
            if border[0] == frames:
                return border[1:]

        return None

    def cache_border_texture(self, frames):
        info =  self.find_border_texture(self)
        if info is not None:
            return info

        # Create nine-patch image and add to cache

    def export(self):
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)

        for name in self.cached_textures:
            for darc in self.archives:
                if darc.has_file("./timg/" + name):
                    bclim = texture.BCLIM(darc.get_file("./timg/" + name))
                    bclim.save_as_png(self.export_dir + name.replace(".bclim", ".png"))