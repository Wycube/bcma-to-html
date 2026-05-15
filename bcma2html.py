import struct, sys, os
import archive, texture


class Canvas:
    def __init__(self, origin_type, canvas_size):
        self.origin_type = origin_type
        self.canvas_size = canvas_size
        self.children = []
    
    def add(self, element):
        self.children.append(element)

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
    
    def print(self):
        str = "Layout: ({}, {})\n".format(self.origin_type, self.canvas_size)

        for child in self.children:
            str += child.print(1)
        
        return str

class TextureList:
    def __init__(self, textures):
        self.textures = textures

    def print(self, level):
        str = " " * level
        str += f"TextureList({self.textures})\n"
        return str

class FontList:
    def __init__(self, fonts):
        self.fonts = fonts

    def print(self, level):
        str = " " * level
        str += f"FontList({self.fonts})\n"
        return str

class MaterialList:
    def __init__(self, materials):
        self.materials = materials

    def print(self, level):
        str = " " * level
        str += f"MaterialList({self.materials})\n"
        return str

class Pane:
    def __init__(self, flags, origin, alpha, padding, name, data, translation, rotation, scale, size):
        self.flags = flags
        self.origin = origin
        self.alpha = alpha
        self.padding = padding
        self.name = name.decode("utf-8").strip('\0')
        self.data = data
        self.translation = translation
        self.rotation = rotation
        self.scale = scale
        self.size = size
        self.children = []

    def add(self, element):
        self.children.append(element)

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
        str += "Pane ({}, translation{}, rotation{}, scale{}, size{})\n".format(self.name, self.translation, self.rotation, self.scale, self.size)

        for child in self.children:
            str += child.print(level + 1)

        return str

class Picture:
    def __init__(self, pane_data, tex_data, tex_coords):
        self.name = pane_data[4].decode("utf-8").strip('\0')
        self.pane_data = pane_data
        self.tex_data = tex_data
        self.tex_coords = tex_coords

    def print(self, level):
        str = " " * level
        str += f"Picture({self.name}, material({self.tex_data[16]}), tex_coords{self.tex_coords})\n"
        return str

class Text:
    def __init__(self, flags, origin, alpha, padding, name, data, translation, rotation, scale, size, 
                 h_flags, v_flags, material_id, flags_2, padding_2, top_color, bottom_color, font_scale, h_font_space, v_font_space, text):
        self.flags = flags
        self.origin = origin
        self.alpha = alpha
        self.padding = padding
        self.name = name.decode("utf-8").strip('\0')
        self.data = data
        self.translation = translation
        self.rotation = rotation
        self.scale = scale
        self.size = size
        self.h_flags = h_flags
        self.v_flags = v_flags
        self.material_id = material_id
        self.flags_2 = flags_2
        self.padding_2 = padding_2
        self.top_color = top_color
        self.bottom_color = bottom_color
        self.font_scale = font_scale
        self.h_font_space = h_font_space
        self.v_font_space = v_font_space
        self.text = text

    def print(self, level):
        str = " " * level
        str += "Text: ({}, translation{}, rotation{}, scale{}, size{}, font_scale{}, horiz_space({}), vert_space({}), h_flags({}), v_flags({}), flags({}), material_id({}), padding({}), text:'{}')\n".format(self.name, self.translation, self.rotation, self.scale, self.size, self.font_scale, self.h_font_space, self.v_font_space, self.h_flags, self.v_flags, self.flags_2, self.material_id, self.padding_2, self.text)
        return str

class Window:
    def __init__(self):
        pass

    def print(self, level):
        str = " " * level
        str += "Window\n"
        return str

class Bounding:
    def __init__(self):
        pass

    def print(self, level):
        str = " " * level
        str += "Bounding\n"
        return str

class Group:
    def __init__(self, name, refs):
        self.name = name.decode("utf-8").strip('\0')
        self.refs = refs

    def print(self, level):
        str = " " * level
        str += "Group({}, {})\n".format(self.name, self.refs)
        return str

class UserData:
    def __init__(self, dict):
        self.dict = dict

    def print(self, level):
        str = " " * level
        str += "UserData({})\n".format(self.dict)
        return str

class LayoutTree:
    def __init__(self, canvas_layout):
        self.root = canvas_layout
        self.pane_stack = []
        self.last_pane = None

    def add_element(self, element):
        if len(self.pane_stack) == 0:
            self.root.add(element)
        else:
            self.pane_stack[-1].add(element)
        
        if type(element) == Pane:
            self.last_pane = element

    def push_pane(self):
        self.pane_stack.append(self.last_pane)

    def pop_pane(self):
        self.pane_stack.pop()

    def push_group(self):
        pass

    def pop_group(self):
        pass

    def print(self):
        return self.root.print()
    
    def get_user_data(self, name):
        return self.root.get_user_data(name)
    
    def get_named_obj(self, name):
        return self.root.get_named_obj(name)

def parse_lyt1(buffer, offset):
    layout_data = struct.unpack("<I2f", buffer[offset + 8:offset + 20])

    return LayoutTree(Canvas(layout_data[0], layout_data[1:]))

def parse_txl1(buffer, offset):
    num_textures = struct.unpack("<I", buffer[offset + 8:offset + 12])[0]
    name_offsets = struct.unpack(f"<{num_textures}I", buffer[offset + 12:offset + 12 + 4 * num_textures])
    start_pos = offset + 12
    textures = []

    for name_offset in name_offsets:
        term_pos = buffer.find(b'\x00', start_pos + name_offset)
        name = buffer[start_pos + name_offset:term_pos].decode()
        textures.append(name)

    return TextureList(textures)

def parse_fnl1(buffer, offset):
    num_fonts = struct.unpack("<I", buffer[offset + 8:offset + 12])[0]
    name_offsets = struct.unpack(f"<{num_fonts}I", buffer[offset + 12:offset + 12 + 4 * num_fonts])
    start_pos = offset + 12
    fonts = []

    for name_offset in name_offsets:
        term_pos = buffer.find(b'\x00', start_pos + name_offset)
        name = buffer[start_pos + name_offset:term_pos].decode()
        fonts.append(name)

    return FontList(fonts)

def parse_mat1(buffer, offset):
    num_entries = struct.unpack("<I", buffer[offset + 8:offset + 12])[0]
    entry_offsets = struct.unpack(f"<{num_entries}I", buffer[offset + 12:offset + 12 + 4 * num_entries])
    materials = []

    for entry_offset in entry_offsets:
        material = struct.unpack("<20s4B24BI", buffer[offset + entry_offset:offset + entry_offset + 0x34])
        name = material[0].decode().strip('\0')
        
        num_tex_maps = material[29] & 3
        tex_maps = []
        for i in range(num_tex_maps):
            tex_maps.append(struct.unpack("<HBB", buffer[offset + entry_offset + 0x34 + 4 * i:offset + entry_offset + 0x34 + 4 * (i + 1)]))
        
        
        materials.append(name)

    return MaterialList(materials)

def parse_pan1(buffer, offset):
    layout_data = struct.unpack("<bbbb16s8s3f3f2f2f", buffer[offset + 8:offset + 0x4C])

    return Pane(*layout_data[:6], layout_data[6:9], layout_data[9:12], layout_data[12:14], layout_data[14:])

def parse_pic1(buffer, offset):
    pane_data = struct.unpack("<bbbb16s8s3f3f2f2f", buffer[offset + 8:offset + 0x4C])
    tex_data = struct.unpack("<4B4B4B4BHH", buffer[offset + 0x4C:offset + 0x60])
    tex_coords = []

    for i in range(tex_data[17]):
        coord_data = struct.unpack("<2f2f2f2f", buffer[offset + 0x60 + 0x20 * i:offset + 0x60 + 0x20 * (i + 1)])
        tex_coords.append(coord_data)

    return Picture(pane_data, tex_data, tex_coords)

def parse_txt1(buffer, offset):
    pane_data = struct.unpack("<bbbb16s8s3f3f2f2f", buffer[offset + 8:offset + 0x4C])
    text_data = struct.unpack("<HHIHHIII2fff", buffer[offset + 0x4C:offset + 0x74])
    text_offset = text_data[5]
    string = buffer[offset + text_offset:offset + struct.unpack("<I", buffer[offset + 4:offset + 8])[0]].decode("utf-16")

    return Text(*pane_data[:6], pane_data[6:9], pane_data[9:12], pane_data[12:14], pane_data[14:], *text_data[:5], *text_data[6:8], text_data[8:10], *text_data[10:], string)

def parse_wnd1(buffer, offset):
    return Window()

def parse_bnd1(buffer, offset):
    return Bounding()

def parse_grp1(buffer, offset):
    group_data = struct.unpack("<16sI", buffer[offset + 8:offset + 0x1C])
    refs = []
    for i in range(group_data[1]):
        entry_off = 0x10 * i
        refs.append(buffer[offset + 0x1C + entry_off:offset + 0x2C + entry_off].decode("utf-8"))

    return Group(group_data[0], refs)

def parse_usd1(buffer : bytes, offset):
    entry_count = struct.unpack("<I", buffer[offset + 8:offset + 0xC])[0]
    dict = {}
    for i in range(entry_count):
        start = offset + 0xC + 0xC * i
        end = start + 0xC
        entry = struct.unpack("<IIHH", buffer[start:end])

        key = buffer[start + entry[0]:].decode("ascii", errors="replace").split('\0')[0]
        value = None
        match entry[3]:
            case 0 : value = buffer[start + entry[1]:start + entry[1] + entry[2]].decode("utf-8")
            case 1 : value = [struct.unpack("<I", buffer[start + entry[1] + i * 4:start + entry[1] + i * 4 + 4])[0] for i in range(entry[2])]
            case 2 : value = [struct.unpack("<f", buffer[start + entry[1] + i * 4:start + entry[1] + i * 4 + 4])[0] for i in range(entry[2])]
        dict[key] = value

    return UserData(dict)

def parse_layout_element(buffer, offset, layout):
    signature = buffer[offset:offset + 4]
    section_size = struct.unpack("<I", buffer[offset + 4:offset + 8])[0]
    # print(signature, section_size)

    match signature:
        case b'lyt1': layout = parse_lyt1(buffer, offset)
        case b'txl1': layout.add_element(parse_txl1(buffer, offset))
        case b'fnl1': layout.add_element(parse_fnl1(buffer, offset))
        case b'mat1': layout.add_element(parse_mat1(buffer, offset))
        case b'pan1': layout.add_element(parse_pan1(buffer, offset))
        case b'pic1': layout.add_element(parse_pic1(buffer, offset))
        case b'txt1': layout.add_element(parse_txt1(buffer, offset))
        case b'wnd1': layout.add_element(parse_wnd1(buffer, offset))
        case b'bnd1': layout.add_element(parse_bnd1(buffer, offset))
        case b'pas1': layout.push_pane()
        case b'pae1': layout.pop_pane()
        case b'grp1': layout.add_element(parse_grp1(buffer, offset))
        case b'grs1': layout.push_group()
        case b'gre1': layout.pop_group()
        case b'usd1': layout.add_element(parse_usd1(buffer, offset))
        case other:
            print("Unknown signature {}!".format(other))
            exit(-1)
    
    return offset + section_size, layout

def parse_layout(buffer, offset):
    layout = None
    while offset < len(buffer):
        offset, layout = parse_layout_element(buffer, offset, layout)

    return layout

def export(trees, path):
    css_name = os.path.basename(path)
    with open(f"{path}.html", "w", encoding="utf-8") as html_file, open(f"{path}.css", "w", encoding="utf-8") as css_file:
        css_file.write("body, div, p {\n")
        css_file.write("    margin: 0;\n")
        css_file.write("    padding: 0;\n")
        css_file.write("}\n")

        html_file.write("<!DOCTYPE html>\n")
        html_file.write("<html>\n")
        html_file.write("    <head>\n")
        html_file.write("        <title>bcma2html test</title>\n")
        html_file.write("        <meta charse=\"utf-8\">\n")
        html_file.write(f"        <link rel=\"stylesheet\" href=\"{css_name}.css\">\n")
        html_file.write("    </head>\n")
        html_file.write("    <body>\n")

        for tree in trees:
            convert(tree.root, html_file, css_file)

        html_file.write("    </body>\n")
        html_file.write("</html>\n")
    
    split = 0
    for tree in trees:
        with open(f"{path}_{split:03}.txt", "w", encoding="utf-8") as text_file:
            convert_txt(tree, text_file)
        split += 1

def convert(node, html_file, css_file):
    if type(node) == Pane:
        html_file.write("<div class=\"{}\">\n".format(node.name))

        css_file.write(".{} {{\n".format(node.name))
        css_file.write("    position: absolute;\n")
        css_file.write("    left: {}px;\n".format(node.translation[0]))
        css_file.write("    top: {}px;\n".format(-node.translation[1]))
        css_file.write("    width: {}px;\n".format(node.size[0]))
        css_file.write("    height: {}px;\n".format(node.size[1]))
        css_file.write("}\n")

    if type(node) == Canvas or type(node) == Pane:
        for child in node.children:
            convert(child, html_file, css_file)
    elif type(node) == Text:
        try:
            html_file.write("<p class=\"{}\">{}</p>\n".format(node.name, node.text))
        except:
            pass

        css_file.write(".{} {{\n".format(node.name))
        css_file.write("    position: absolute;\n")
        css_file.write("    left: {}px;\n".format(node.translation[0]))
        css_file.write("    top: {}px;\n".format(-node.translation[1]))
        css_file.write("    width: {}px;\n".format(node.size[0]))
        css_file.write("    height: {}px;\n".format(node.size[1]))
        css_file.write("    font-size: {}px;\n".format(node.font_scale[1 ]))
        css_file.write("}\n")

    if type(node) == Pane:
        html_file.write("</div>\n")

def convert_txt(tree, text_file):
    text = tree.print()
    text_file.write(text)

def fold_dirs(dirs):
    output_path = dirs[0]
    for dir in dirs[1:]:
        output_path += f"/{dir}"

    return output_path

def main():
    bcma_path = sys.argv[1]
    root_path = os.path.dirname(sys.argv[0])

    # Index the .bcma
    bcma_darc = None
    with open(bcma_path, "rb") as file:
        bcma_darc = archive.DARC(file.read())

    # Get BcmaInfo
    info_darc = archive.DARC(archive.decompress_lz10(bcma_darc.get_file("./BcmaInfo.arc")))
    # 0x14 offset to skip header
    info_tree = parse_layout(info_darc.get_file("./blyt/BcmaInfo.bclyt"), 0x14)
    
    # Get region/language info
    region_info = info_tree.get_user_data("RegionInfo")
    assert(region_info is not None)

    languages = []    
    for i in range(region_info.dict["RegionNum"][0]):
        region_code = region_info.dict["Region_{:03}".format(i)]
        language_info = info_tree.get_user_data(region_code)
        assert(language_info is not None)

        languages.append((region_code, []))
        for j in range(language_info.dict["LangNum"][0]):
            languages[-1][1].append(language_info.dict["Lang_{:03}".format(j)])
    
    # TODO: Get TexRes stuff and load in all required archives beforehand


    # Parse and convert each language
    output_dirs = [f"{root_path}/output"]
    for region in languages:
        output_dirs.append(region[0])
        for lang in region[1]:
            output_dirs.append(lang)
            
            if not os.path.exists(fold_dirs(output_dirs)):
                os.makedirs(fold_dirs(output_dirs))

            # Get Index.bclyt
            index_darc = archive.DARC(archive.decompress_lz10(bcma_darc.get_file(f"./{region[0]}_{lang}_index.arc")))
            index_tree = parse_layout(index_darc.get_file("./blyt/Index.bclyt"), 0x14)
            
            # Get metadata
            metadata = index_tree.get_user_data("MetaData")
            assert(metadata is not None)

            # Get page titles
            titles = []
            for i in range(metadata.dict["PageNum"][0]):
                page_title = index_tree.get_named_obj(f"PageTitle_{i:03}")
                assert(page_title is not None)
                titles.append(page_title.text)
                
            # Get categories
            categories = []
            for i in range(metadata.dict["CategoryNum"][0]):
                category = index_tree.get_user_data(f"Category_{i:03}")
                category_title = index_tree.get_named_obj(f"Category_{i:03}")
                assert(category is not None)
                assert(category_title is not None)


            # Convert each page (small ones for now)
            for i, splits in enumerate(metadata.dict["SplitNumS"]):
                page_darc = archive.DARC(archive.decompress_lz10(bcma_darc.get_file(f"./{region[0]}_{lang}_small.arc")))
                page_trees = []

                for split in range(splits):
                    page_file = page_darc.get_file(f"./blyt/Page_{i:03}_small_{split}.bclyt")
                    page_trees.append(parse_layout(page_file, 0x14))
                

                output_path = fold_dirs(output_dirs)
                export(page_trees, f"{output_path}/Page_{i:03}")


            output_dirs.pop()
        output_dirs.pop()


    print("Successfully Completed!")


main()