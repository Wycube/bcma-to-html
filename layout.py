import struct
import texture


class Named:
    def __init__(self, name):
        self.name = name

class PaneData:
    def __init__(self, data):
        pane_data = struct.unpack("<bbbx16s8s3f3f2f2f", data[8:0x4C])
        self.flags = pane_data[0]
        self.origin = pane_data[1]
        self.alpha = pane_data[2]
        self.name = pane_data[3].decode("utf-8").strip('\0')
        self.data_str = pane_data[4]
        self.translation = (pane_data[5], pane_data[6], pane_data[7])
        self.rotation = (pane_data[8], pane_data[9], pane_data[10])
        self.scale = (pane_data[11], pane_data[12])
        self.size = (pane_data[13], pane_data[14])

class TextureList:
    def parse_txl1(data):
        num_textures = struct.unpack("<I", data[8:12])[0]
        name_offsets = struct.unpack(f"<{num_textures}I", data[12:12 + 4 * num_textures])
        textures = []

        for name_offset in name_offsets:
            term_pos = data.find(b'\x00', 12 + name_offset)
            name = data[12 + name_offset:term_pos].decode()
            textures.append(name)

        return textures

    def __init__(self, data):
        self.textures = TextureList.parse_txl1(data)

    def print(self, level):
        str = " " * level
        str += f"TextureList({self.textures})\n"
        return str
    
    def offset_material_id(self, _):
        pass

class FontList:
    def parse_fnl1(data):
        num_fonts = struct.unpack("<I", data[8:12])[0]
        name_offsets = struct.unpack(f"<{num_fonts}I", data[12:12 + 4 * num_fonts])
        fonts = []

        for name_offset in name_offsets:
            term_pos = data.find(b'\x00', 12 + name_offset)
            name = data[12 + name_offset:term_pos].decode()
            fonts.append(name)

        return fonts

    def __init__(self, data):
        self.fonts = FontList.parse_fnl1(data)

    def print(self, level):
        str = " " * level
        str += f"FontList({self.fonts})\n"
        return str
    
    def offset_material_id(self, _):
        pass

class MaterialList:
    def parse_mat1(data):
        num_entries = struct.unpack("<I", data[8:12])[0]
        entry_offsets = struct.unpack(f"<{num_entries}I", data[12:12 + 4 * num_entries])
        materials = []

        for entry_offset in entry_offsets:
            material = struct.unpack("<20s4B24BI", data[entry_offset:entry_offset + 0x34])
            assert (material[29] >> 6) & 0x1F == 0, "Materials components beyond texCoordGen are not handled yet!"
            
            num_tex_maps = material[29] & 3
            tex_maps = []
            for i in range(num_tex_maps):
                tex_maps.append(struct.unpack("<HBB", data[entry_offset + 0x34 + 4 * i:entry_offset + 0x34 + 4 * (i + 1)]))
            
            num_tex_mats = (material[29] >> 2) & 3
            tex_mats = []
            tex_mats_start = entry_offset + 0x34 + 4 * num_tex_maps
            for i in range(num_tex_mats):
                tex_mats.append(struct.unpack("<2ff2f", data[tex_mats_start + 20 * i:tex_mats_start + 20 * (i + 1)]))
            
            num_tex_coords = (material[29] >> 4) & 3
            tex_coords = []
            tex_coords_start = tex_mats_start + 20 * num_tex_mats
            for i in range(num_tex_coords):
                tex_coords.append(struct.unpack("<2bxx", data[tex_coords_start + 4 * i:tex_coords_start + 4 * (i + 1)]))
            
            materials.append((material, tex_maps, tex_mats, tex_coords))

        return materials

    def __init__(self, data):
        self.materials = MaterialList.parse_mat1(data)

    def print(self, level):
        str = " " * level
        str += f"MaterialList({self.materials})\n"
        return str
    
    def offset_material_id(self, _):
        pass

class Pane(Named):
    def parse_pan1(data):
        return PaneData(data)

    def __init__(self, data):
        self.pane_data = Pane.parse_pan1(data)
        self.children = []
        super(Pane, self).__init__(self.pane_data.name)

    def get_user_data(self, name):
        # Look through all layers and find a pane/text matching the name.
        # If there is a user data after it, return that.
        check_next = False
        for obj in self.children:
            if check_next and isinstance(obj, UserData):
                return obj
            else:
                check_next = False

            if isinstance(obj, Pane):
                result = obj.get_user_data(name)
                if result is not None:
                    return result

                check_next = obj.name == name

            if isinstance(obj, Text):
                check_next = obj.name == name

        return None

    def get_named_obj(self, name):
        # Look through all layers and find a pane/text/group matching the name.
        for obj in self.children:
            if not (isinstance(obj, Pane) or isinstance(obj, Text) or isinstance(obj, Group)):
                continue

            if isinstance(obj, Pane) and obj.name != name:
                result = obj.get_named_obj(name)
                if result is not None:
                    return result
                continue

            if obj.name == name:
                return obj

        return None

    def print(self, level):
        str = " " * level
        str += "Pane ({}, translation{}, rotation{}, scale{}, size{})\n".format(self.name, self.pane_data.translation, self.pane_data.rotation, self.pane_data.scale, self.pane_data.size)

        for child in self.children:
            str += child.print(level + 1)

        return str
    
    def offset_material_id(self, offset):
        for obj in self.children:
            obj.offset_material_id(offset)

class Picture(Named):
    def parse_pic1(data):
        tex_data = struct.unpack("<4B4B4B4BHH", data[0x4C:0x60])
        tex_coords = []

        for i in range(tex_data[17]):
            coord_data = struct.unpack("<2f2f2f2f", data[0x60 + 0x20 * i:0x60 + 0x20 * (i + 1)])
            tex_coords.append(coord_data)

        return PaneData(data), tex_data, tex_coords

    def __init__(self, data):
        self.pane_data, self.tex_data, self.tex_coords = Picture.parse_pic1(data)
        super(Picture, self).__init__(self.pane_data.name)

    def print(self, level):
        str = " " * level
        str += f"Picture({self.name}, material({self.tex_data[16]}), tex_coords{self.tex_coords})\n"
        return str
    
    def offset_material_id(self, offset):
        # self.tex_data[16] += offset
        self.tex_data = (*self.tex_data[:16], self.tex_data[16] + offset, *self.tex_data[16:])


class Text(Named):
    def parse_txt1(data):
        text_data = struct.unpack("<HHHHH2xIII2fff", data[0x4C:0x74])
        text_start = text_data[5]
        text_end = struct.unpack("<I", data[4:8])[0]
        string = data[text_start:text_end].decode("utf-16-le")

        return PaneData(data), text_data, string

    def __init__(self, data):
        self.pane_data, text_data, self.text = Text.parse_txt1(data)
        self.h_flags = text_data[0]
        self.v_flags = text_data[1]
        self.material_id = text_data[2]
        self.font_id = text_data[3]
        self.flags_2 = text_data[4]
        self.top_color = text_data[6]
        self.bottom_color = text_data[7]
        self.font_scale = (text_data[8], text_data[9])
        self.h_font_space = text_data[10]
        self.v_font_space = text_data[11]
        super(Text, self).__init__(self.pane_data.name)

    def print(self, level):
        str = " " * level
        str += "Text: ({}, translation{}, rotation{}, scale{}, size{}, font_scale{}, horiz_space({}), vert_space({}), h_flags({}), v_flags({}), flags({}), material_id({}), text:'{}')\n".format(self.name, self.pane_data.translation, self.pane_data.rotation, self.pane_data.scale, self.pane_data.size, self.font_scale, self.h_font_space, self.v_font_space, self.h_flags, self.v_flags, self.flags_2, self.material_id, self.text)
        return str
    
    def offset_material_id(self, offset):
        self.material_id += offset

class Window(Named):
    def parse_wnd1(data):
        wind_data = struct.unpack("<4f2b2x2I", data[0x4C:0x68])
        assert wind_data[4] in (1, 4, 8), f"Window frame count ({wind_data[4]}) not supported!"

        # Content Pane stuff
        cont_data = struct.unpack("4I2H", data[wind_data[6]:wind_data[6] + 0x14])
        start = wind_data[6] + 0x14
        tex_coords = []

        for i in range(cont_data[5]):
            coord_data = struct.unpack("<2f2f2f2f", data[start + 0x20 * i:start + 0x20 * (i + 1)])
            tex_coords.append(coord_data)
        
        # Frames stuff
        start = wind_data[7]
        frames = []

        for i in range(wind_data[4]):
            frame_offset = struct.unpack("<I", data[start + 4 * i:start + 4 * (i + 1)])[0]
            frame_data = struct.unpack("<Hbx", data[frame_offset:frame_offset + 4])
            frames.append(frame_data)

        return PaneData(data), wind_data, cont_data, tex_coords, frames

    def __init__(self, data):
        self.pane_data, self.wind_data, self.cont_data, self.tex_coords, self.frames = Window.parse_wnd1(data)
        super(Window, self).__init__(self.pane_data.name)

    def print(self, level):
        str = " " * level
        str += f"Window({self.name}, {self.wind_data}, {self.cont_data}, {self.tex_coords}, {self.frames})\n"
        return str
    
    def offset_material_id(self, offset):
        # self.cont_data[4] += offset
        self.cont_data = (*self.cont_data[:4], self.cont_data[4] + offset, *self.cont_data[5:])
        for i, frame in enumerate(self.frames):
            # frame[0] += offset
            self.frames[i] = (frame[0] + offset, *frame[1:])
    
    def load_texture_sizes(self, mat_list, tex_list, tex_cache):
        self.frame_sizes = []
        frame_infos = []

        for frame in self.frames:
            material_id = frame[0]
            material = mat_list.materials[material_id]
            if len(material[1]) != 0:
                tex_name = tex_list.textures[material[1][0][0]]
                for darc in tex_cache.archives:
                    if darc.has_file("./timg/" + tex_name):
                        self.frame_sizes.append(texture.BCLIM.get_size(darc.get_file("./timg/" + tex_name)))
                        frame_infos.append((tex_name, frame[1]))
                        break
            else:
                self.frame_sizes.append((0, 0))
                frame_infos = None
        
        self.calc_sizes()

        self.border_image_name = None
        if frame_infos is not None:
            self.border_image_name = tex_cache.cache_border(frame_infos)[1]

    def calc_sizes(self):
        self.content_box = [0, self.pane_data.size[0], 0, self.pane_data.size[1]]

        frames = self.wind_data[4]
        match frames:
            case 1:
                self.content_box[0] += self.frame_sizes[0][0]
                self.content_box[1] -= self.frame_sizes[0][0]
                self.content_box[2] += self.frame_sizes[0][1]
                self.content_box[3] -= self.frame_sizes[0][1]
            case 4:
                # Assuming widths and heights of aligned corners are the same
                self.content_box[0] += self.frame_sizes[0][0]
                self.content_box[1] -= self.frame_sizes[1][0]
                self.content_box[2] += self.frame_sizes[0][1]
                self.content_box[3] -= self.frame_sizes[2][1]
            case 8:
                # TODO: Add assert that sides' and corners' dimensions match
                assert False, "8 frame windows are unimplemented!"

class Bounding:
    def parse_bnd1(data):
        pass

    def __init__(self, data):
        assert False, "Bounding element unimplemented!"

class Group(Named):
    def parse_grp1(data):
        group_data = struct.unpack("<16sI", data[8:0x1C])
        refs = []
        for i in range(group_data[1]):
            entry_off = 0x10 * i
            refs.append(data[0x1C + entry_off:0x2C + entry_off].decode("utf-8"))

        return group_data[0].decode("utf-8").strip('\0'), refs

    def __init__(self, data):
        name, self.refs = Group.parse_grp1(data)
        super(Group, self).__init__(name)

    def print(self, level):
        str = " " * level
        str += "Group({}, {})\n".format(self.name, self.refs)
        return str
    
    def offset_material_id(self, _):
        pass

class UserData:
    def parse_usd1(data):
        entry_count = struct.unpack("<I", data[8:0xC])[0]
        dict = {}
        for i in range(entry_count):
            start = 0xC + 0xC * i
            end = start + 0xC
            entry = struct.unpack("<IIHH", data[start:end])

            key = data[start + entry[0]:].decode("ascii", errors="replace").split('\0')[0]
            value = None
            match entry[3]:
                case 0 : value = data[start + entry[1]:start + entry[1] + entry[2]].decode("utf-8")
                case 1 : value = [struct.unpack("<I", data[start + entry[1] + i * 4:start + entry[1] + i * 4 + 4])[0] for i in range(entry[2])]
                case 2 : value = [struct.unpack("<f", data[start + entry[1] + i * 4:start + entry[1] + i * 4 + 4])[0] for i in range(entry[2])]
                case other: assert False, f"Unknown usd1 entry type ({entry[3]})"
            dict[key] = value

        return dict

    def __init__(self, data):
        self.dict = UserData.parse_usd1(data)

    def print(self, level):
        str = " " * level
        str += "UserData({})\n".format(self.dict)
        return str
    
    def offset_material_id(self, _):
        pass

class LayoutTree:
    def parse_lyt1(data):
        assert data[:4] == b'lyt1', "Layouts should start with a lyt1!"

        layout_data = struct.unpack("<II2f", data[4:20])
        return layout_data

    def __init__(self, data):
        lyt1 = LayoutTree.parse_lyt1(data)
        self.origin_type = lyt1[1]
        self.canvas_size = (lyt1[2], lyt1[3])

        self.children = []
        self.pane_stack = []
        self.last_pane = None
        self.parse_tree(data, lyt1[0])

    def parse_layout_element(self, data, offset):
        signature = data[offset:offset + 4]
        section_size = struct.unpack("<I", data[offset + 4:offset + 8])[0]
        # print(signature, section_size)

        match signature:
            case b'lyt1': assert False, "There should only be a lyt1 at the root!"
            case b'txl1': 
                assert len(self.pane_stack) == 0 and self.last_pane is None, "Resources lists should be defined first in the layout!"
                self.add_obj(TextureList(data[offset:]))
            case b'fnl1': 
                assert len(self.pane_stack) == 0 and self.last_pane is None, "Resources lists should be defined first in the layout!"
                self.add_obj(FontList(data[offset:]))
            case b'mat1': 
                assert len(self.pane_stack) == 0 and self.last_pane is None, "Resources lists should be defined first in the layout!"
                self.add_obj(MaterialList(data[offset:]))
            case b'pan1': self.add_obj(Pane(data[offset:]))
            case b'pic1': self.add_obj(Picture(data[offset:]))
            case b'txt1': self.add_obj(Text(data[offset:]))
            case b'wnd1': self.add_obj(Window(data[offset:]))
            case b'bnd1': self.add_obj(Bounding(data[offset:]))
            case b'pas1': self.push_pane()
            case b'pae1': self.pop_pane()
            case b'grp1': self.add_obj(Group(data[offset:]))
            case b'grs1': self.push_group()
            case b'gre1': self.pop_group()
            case b'usd1': self.add_obj(UserData(data[offset:]))
            case other: assert False, f"Unknown signature {other}!"
        
        return offset + section_size

    def parse_tree(self, data, offset):
        while offset < len(data):
            offset = self.parse_layout_element(data, offset)

    def add_obj(self, element):
        if len(self.pane_stack) == 0:
            self.children.append(element)
        else:
            self.pane_stack[-1].children.append(element)
        
        if type(element) == Pane:
            self.last_pane = element

    def push_pane(self):
        self.pane_stack.append(self.last_pane)

    def pop_pane(self):
        self.pane_stack.pop()

    def push_group(self):
        assert False, "Push group unimplemented!"

    def pop_group(self):
        assert False, "Pop group unimplemented!"

    def print(self):
        str = "Layout: ({}, {})\n".format(self.origin_type, self.canvas_size)

        for child in self.children:
            str += child.print(1)
        
        return str
    
    def get_user_data(self, name):
        # Look through all layers and find a pane/text matching the name.
        # If there is a user data after it, return that.
        check_next = False
        for obj in self.children:
            if check_next and isinstance(obj, UserData):
                return obj
            else:
                check_next = False

            if isinstance(obj, Pane):
                result = obj.get_user_data(name)
                if result is not None:
                    return result

            if isinstance(obj, Named):
                check_next = obj.name == name

        return None

    def get_named_obj(self, name):
        # Look through all layers and find a pane/text/group matching the name.
        for obj in self.children:
            if not isinstance(obj, Named):
                continue

            if isinstance(obj, Pane) and obj.name != name:
                result = obj.get_named_obj(name)
                if result is not None:
                    return result
                continue

            if obj.name == name:
                return obj

        return None

    def get_toplevel_obj_of_type(self, type_name):
        for child in self.children:
            if type(child) is type_name:
                return child
        
        return None
    
    def _offset_material_indices(self, offset):
        for obj in self.children:
            obj.offset_material_id(offset)

    def merge(self, other):
        # Take maximum bounding box for size if sizes differ
        new_size = self.canvas_size
        if self.canvas_size != other.canvas_size:
            new_size = (max(self.canvas_size[0], other.canvas_size[0]), max(self.canvas_size[1]), other.canvas_size[1])
        self.canvas_size = new_size

        # I've never seen any other fonts used so I'd be curious to see this fail
        fonts_list_1 = self.get_toplevel_obj_of_type(FontList)
        fonts_list_2 = other.get_toplevel_obj_of_type(FontList)
        if fonts_list_1 is not None and fonts_list_2 is not None:
            assert fonts_list_1.fonts == fonts_list_2.fonts == ["cbf_std.bcfnt"]
        elif fonts_list_2 is not None:
            self.children.insert(0, fonts_list_2)
        
        # Update texture indices in the other layout's material list
        tex_list_1 = self.get_toplevel_obj_of_type(TextureList)
        tex_list_2 = other.get_toplevel_obj_of_type(TextureList)
        if tex_list_1 is not None and tex_list_2 is not None:
            size = len(tex_list_1.textures)
            mat_list = other.get_toplevel_obj_of_type(MaterialList)
            for material in mat_list.materials:
                for i, tex_map in enumerate(material[1]):
                    material[1][i] = (tex_map[0] + size, tex_map[1], tex_map[2])
            
            tex_list_1.textures.extend(tex_list_2.textures)
        elif tex_list_2 is not None:
            self.children.insert(0, tex_list_2)

        # Update material indices in the other layout's elements
        mat_list_1 = self.get_toplevel_obj_of_type(MaterialList)
        mat_list_2 = other.get_toplevel_obj_of_type(MaterialList)
        if mat_list_1 is not None and mat_list_2 is not None:
            size = len(mat_list_1.materials)
            other._offset_material_indices(size)
            mat_list_1.materials.extend(mat_list_2.materials)
        elif mat_list_2 is not None:
            self.children.insert(0, mat_list_2)

        # Add children from other layout sans the resource lists
        for child in other.children:
            if not (isinstance(child, TextureList) or isinstance(child, FontList) or isinstance(child, MaterialList)):
                self.children.append(child)

class BCLYT:
    def parse_header(data):
        assert data[:4] == b'CLYT', f"Invalid header {data[:4]}, expecting {b'CLYT'}!"
        assert data[4:6] == b'\xFF\xFE', "Invalid byte order mark, big endian not supported!"

        header = struct.unpack("<HIIH", data[6:18])
        return header

    def __init__(self, data):
        self.header = BCLYT.parse_header(data)
        self.layout = LayoutTree(data[20:])