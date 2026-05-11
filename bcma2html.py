import struct, sys


class Canvas:
    def __init__(self, origin_type, canvas_size):
        self.origin_type = origin_type
        self.canvas_size = canvas_size
        self.children = []
    
    def add(self, element):
        self.children.append(element)
    
    def print(self):
        str = "Layout: ({}, {})\n".format(self.origin_type, self.canvas_size)

        for child in self.children:
            str += child.print(1)
        
        return str

class TextureList:
    def __init__(self):
        pass

    def print(self, level):
        str = " " * level
        str += "TextureList\n"
        return str

class FontList:
    def __init__(self):
        pass

    def print(self, level):
        str = " " * level
        str += "FontList\n"
        return str

class MaterialList:
    def __init__(self):
        pass

    def print(self, level):
        str = " " * level
        str += "MaterialList\n"
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
    
    def print(self, level):
        str = " " * level
        str += "Pane ({}, translation{}, rotation{}, scale{}, size{})\n".format(self.name, self.translation, self.rotation, self.scale, self.size)

        for child in self.children:
            str += child.print(level + 1)

        return str

class Picture:
    def __init__(self):
        pass

    def print(self, level):
        str = " " * level
        str += "Picture\n"
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
        str += "Text: ({}, translation{}, rotation{}, scale{}, size{}, font_scale{}, horiz_space({}), vert_space({}), h_flags({}), v_flags({}), flags({}), padding({}), text:'{}')\n".format(self.name, self.translation, self.rotation, self.scale, self.size, self.font_scale, self.h_font_space, self.v_font_space, self.h_flags, self.v_flags, self.flags_2, self.padding_2, self.text)
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

def parse_lyt1(buffer, offset):
    layout_data = struct.unpack("<I2f", buffer[offset + 8:offset + 20])

    return LayoutTree(Canvas(layout_data[0], layout_data[1:]))

def parse_txl1(buffer, offset):
    return TextureList()

def parse_fnl1(buffer, offset):
    return FontList()

def parse_mat1(buffer, offset):
    return MaterialList()

def parse_pan1(buffer, offset):
    layout_data = struct.unpack("<bbbb16s8s3f3f2f2f", buffer[offset + 8:offset + 0x4C])
    print(layout_data)

    return Pane(*layout_data[:6], layout_data[6:9], layout_data[9:12], layout_data[12:14], layout_data[14:])

def parse_pic1(buffer, offset):
    return Picture()

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
    print(group_data[1])
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
    print(signature, section_size)

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

def convert_txt(tree, text_file, depth):
    text = tree.print()
    text_file.write(text)

def main():
    bcma_path = sys.argv[1]

    buffer = None
    with open(bcma_path, "rb") as file:
        buffer = file.read()
    
    layout_tree = parse_layout(buffer, 0x14)

    # Get all files from the archive


    # Decompress all the files


    # Convert the bclyt
    with open("output/out.html", "w") as html_file, open("output/out.css", "w") as css_file:
        css_file.write("body, div, p {\n")
        css_file.write("    margin: 0;\n")
        css_file.write("    padding: 0;\n")
        css_file.write("}\n")

        html_file.write("<!DOCTYPE html>\n")
        html_file.write("<html>\n")
        html_file.write("    <head>\n")
        html_file.write("        <title>bcma2html test</title>\n")
        html_file.write("        <meta charse=\"utf-8\">\n")
        html_file.write("        <link rel=\"stylesheet\" href=\"out.css\">\n")
        html_file.write("    </head>\n")
        html_file.write("    <body>\n")

        convert(layout_tree.root, html_file, css_file)

        html_file.write("    </body>\n")
        html_file.write("</html>\n")
    
    with open("output/out.txt", "w", encoding="utf-8") as text_file:
        convert_txt(layout_tree, text_file, 0)
    
    print("Successfully Completed!")


main()