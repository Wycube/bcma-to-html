import struct, sys, os, argparse
import texture, layout, manual
import PIL.Image


class HTMLWriter:
    def __init__(self, title, html_path, css_path):
        self.title = title
        self.html_path = html_path
        self.css_path = css_path
        self.body = ""
        self.tabs = 2

    def start_div(self, css_class=None):
        if css_class is not None:
            self.add_raw(f"<div class=\"{css_class}\">")
        else:
            self.add_raw("<div>")
        self.tabs += 1

    def end_div(self):
        self.tabs -= 1
        self.add_raw("</div>")

    def add_raw(self, str):
        self.body += "\t" * self.tabs
        self.body += str
        self.body += "\n"

    def write(self):
        with open(self.html_path, "w", encoding="utf-8") as file:
            file.write("<!DOCTYPE html>\n")
            file.write("<html>\n")
            file.write("\t<head>\n")
            file.write(f"\t\t<title>{self.title}</title>\n")
            file.write("\t\t<meta charset=\"utf-8\">\n")
            
            if self.css_path is not None:
                file.write(f"\t\t<link rel=\"stylesheet\" href=\"{self.css_path}\">\n")

            file.write("\t</head>\n")
            file.write("\t<body>\n")
            file.write(self.body)
            file.write("\t</body>")

class CSSWriter:
    def __init__(self, path):
        self.path = path
        self.selectors = {}
    
    def add_property(self, class_name, name, value):
        if class_name not in self.selectors:
            self.selectors[class_name] = []
        
        self.selectors[class_name].append(f"{name}: {value};")
    
    def write(self):
        with open(self.path, "w", encoding="utf-8") as file:
            for props in self.selectors.items():
                file.write(f"{props[0]} {{\n")
                for property in props[1]:
                    file.write(f"\t{property}\n")
                file.write("}")

def export(trees, tex_archives, path, region_lang):
    split = 0
    for tree in trees:
        with open(f"{path}_{split}.txt", "w", encoding="utf-8") as text_file:
            convert_txt(tree, text_file)
        split += 1

    css_name = os.path.basename(path)
    html = HTMLWriter("bcma2html test", path + ".html", css_name + ".css")
    css = CSSWriter(path + ".css")
    
    # body, div, p
    css.add_property("body, div, p", "margin", "0")
    css.add_property("body, div, p", "padding", "0")
    css.add_property("body, div, p", "box-sizing", "border-box")

    # body
    css.add_property("body", "display", "flex")
    css.add_property("body", "justify-content", "center")

    # .manual
    css.add_property(".manual", "position", "relative")
    css.add_property(".manual", "width", f"{trees[0].canvas_size[0]}px")
    css.add_property(".manual", "height", f"{trees[0].canvas_size[1]}px")
    css.add_property(".manual", "white-space", "preserve nowrap")
    css.add_property(".manual", "overflow", "hidden")

    html.add_raw(f"<a href=\"../../Home_{region_lang}.html\">Home</a>")
    html.start_div("manual")
    for tree in trees:
        convert(tree, tex_archives, tree, path, html, css)
    html.end_div()

    html.write()
    css.write()

def convert(tree, tex_archives, node, path: str, html, css):
    if type(node) == layout.Pane:
        html.start_div(node.name)

        css.add_property(f".{node.name}", "position", "absolute")
        css.add_property(f".{node.name}", "left", f"{node.pane_data.translation[0]}px")
        css.add_property(f".{node.name}", "top", f"{-node.pane_data.translation[1]}px")
        css.add_property(f".{node.name}", "width", f"{node.pane_data.size[0]}px")
        css.add_property(f".{node.name}", "height", f"{node.pane_data.size[1]}px")

    if type(node) == layout.LayoutTree or type(node) == layout.Pane:
        for child in node.children:
            convert(tree, tex_archives, child, path, html, css)
    elif type(node) == layout.Text:
        html.add_raw(f"<p class=\"{node.name}\">{node.text}</p>")

        font_color = struct.unpack("<I", struct.pack(">I", node.top_color))[0]
        css.add_property(f".{node.name}", "position", "absolute")
        css.add_property(f".{node.name}", "left", f"{node.pane_data.translation[0]}px")
        css.add_property(f".{node.name}", "top", f"{-node.pane_data.translation[1]}px")
        css.add_property(f".{node.name}", "width", f"{node.pane_data.size[0]}px")
        css.add_property(f".{node.name}", "height", f"{node.pane_data.size[1]}px")
        css.add_property(f".{node.name}", "font-size", f"{node.font_scale[1]}px")
        css.add_property(f".{node.name}", "color", f"#{font_color:08X}")
    elif type(node) == layout.Picture:
        assert node.tex_coords == [(0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0)], f"Texcoords other than default not handled yet! {node.tex_coords}"
        for col in node.tex_data[:16]:
            assert col == 255, "Vertex other than white not handled yet!"
        
        mat_list = tree.get_toplevel_obj_of_type(layout.MaterialList)
        tex_list = tree.get_toplevel_obj_of_type(layout.TextureList)
        assert mat_list is not None and tex_list is not None, "Material list or texture list missing!"
        
        mat_index = node.tex_data[16]
        tex_index = mat_list.materials[mat_index][1][0][0]
        tex_name: str = tex_list.textures[tex_index]
        tex_name_png = tex_name.replace(".bclim", ".png")

        html.add_raw(f"<img src=\"{tex_name_png}\" class=\"{node.name}\">")

        css.add_property(f".{node.name}", "position", "absolute")
        css.add_property(f".{node.name}", "left", f"{node.pane_data.translation[0]}px")
        css.add_property(f".{node.name}", "top", f"{-node.pane_data.translation[1]}px")
        css.add_property(f".{node.name}", "width", f"{node.pane_data.size[0]}px")
        css.add_property(f".{node.name}", "height", f"{node.pane_data.size[1]}px")

        for darc in tex_archives:
            if darc.has_file("./timg/" + tex_name):
                bclim = texture.BCLIM(darc.get_file("./timg/" + tex_name))
                bclim.save_as_png(path[:path.rfind('/')] + "/" + tex_name_png)
    elif type(node) == layout.Window:
        mat_list = tree.get_toplevel_obj_of_type(layout.MaterialList)
        tex_list = tree.get_toplevel_obj_of_type(layout.TextureList)
        assert mat_list is not None, "Material list missing!"
        
        mat_index = node.cont_data[4]
        tex_index = mat_list.materials[mat_index][1]
        back_color = struct.unpack("<I", struct.pack(">I", node.cont_data[0]))[0]

        node.load_texture_sizes(mat_list, tex_list, tex_archives)
        css.add_property(f".{node.name}", "position", "absolute")
        css.add_property(f".{node.name}", "left", f"{node.pane_data.translation[0]}px")
        css.add_property(f".{node.name}", "top", f"{-node.pane_data.translation[1]}px")
        css.add_property(f".{node.name}", "width", f"{node.content_box[1] - node.content_box[0]}px")
        css.add_property(f".{node.name}", "height", f"{node.content_box[3] - node.content_box[2]}px")
        css.add_property(f".{node.name}", "background-color", f"#{back_color:08X}")

        if node.border_image is not None:
            border_sizes = (node.content_box[2], node.pane_data.size[0] - node.content_box[1], node.pane_data.size[1] - node.content_box[3], node.content_box[0])
            css.add_property(f".{node.name}", "border", "solid transparent")
            css.add_property(f".{node.name}", "border-top-width", f"{border_sizes[0]}px")
            css.add_property(f".{node.name}", "border-right-width", f"{border_sizes[1]}px")
            css.add_property(f".{node.name}", "border-bottom-width", f"{border_sizes[2]}px")
            css.add_property(f".{node.name}", "border-left-width", f"{border_sizes[3]}px")
            css.add_property(f".{node.name}", "border-image", "url(\"{}\")".format(path[path.rfind('/') + 1:] + "_" + node.name + ".png"))
            css.add_property(f".{node.name}", "border-image-slice", "{} {} {} {}".format(*border_sizes))
            css.add_property(f".{node.name}", "box-sizing", "content-box")
            css.add_property(f".{node.name}", "background-clip", "padding-box")
        
        if len(tex_index) == 1:
            assert tex_list is not None, "Texture list missing!"
            tex_name: str = tex_list.textures[tex_index[0][0]]
            tex_name_png = tex_name.replace(".bclim", ".png")
            css.add_property(f".{node.name}", "background-image", "url(\"{}\")".format(tex_name_png))
            for darc in tex_archives:
                if darc.has_file("./timg/" + tex_name):
                    bclim = texture.BCLIM(darc.get_file("./timg/" + tex_name))
                    bclim.save_as_png(path[:path.rfind('/')] + "/" + tex_name_png)

        html.add_raw(f"<div class=\"{node.name}\"></div>")

        if node.border_image is not None:
            export = PIL.Image.new("RGBA", node.border_image_size)
            export.frombytes(bytes(node.border_image))
            export.save(path + "_" + node.name + ".png", format="png")

    if type(node) == layout.Pane:
        html.end_div()

def convert_txt(tree, text_file):
    text = tree.print()
    text_file.write(text)

def fold_dirs(dirs):
    output_path = dirs[0]
    for dir in dirs[1:]:
        output_path += f"/{dir}"

    return output_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manual", help="Path to the BCMA file (usually Manual.bcma)")
    args = parser.parse_args()

    bcma_path = args.manual
    root_path = os.path.dirname(sys.argv[0])

    # Read in the .bcma
    bcma = None
    with open(bcma_path, "rb") as file:
        bcma = manual.BCMA(file.read())

    # Convert each language
    categories_html = {}
    output_dirs = [f"{root_path}/output"]
    for region in bcma.regions:
        output_dirs.append(region[0])
        for lang in region[1]:
            lang_str = f"{region[0]}_{lang}"
            output_dirs.append(lang)
            
            if not os.path.exists(fold_dirs(output_dirs)):
                os.makedirs(fold_dirs(output_dirs))

            # Make HTML for home page category links
            category_html = ""
            for category in bcma.get_categories(f"{region[0]}_{lang}"):
                category_html += "<div class=\"category-block\">"
                if category[1]:
                    category_html += "<p class=\"category\">{}</p>".format(category[0])
                
                for page in category[2]:
                    category_html += "<a class=\"page\" href=\"{}/{}/Page_{:03}.html\"><div class=\"icon\">{}</div>{}</a>".format(region[0], lang, page, 1 + page, bcma.get_page_title(lang_str, page))
                category_html += "</div>"
            categories_html[lang_str] = category_html

            # Convert each page (small ones for now)
            for i in range(bcma.get_page_count(lang_str)):
                # page_trees = []
                page_tree = None

                # Background
                page_file = bcma.get_page_bg(lang_str, i)
                # page_trees.append(page_file.layout)
                page_tree = page_file.layout
                
                for split in range(bcma.get_page_splits(lang_str, i)):
                    page_file = bcma.get_page_split(lang_str, i, split)
                    page_tree.merge(page_file.layout)
                
                output_path = fold_dirs(output_dirs)
                export([page_tree], bcma.tex_archives, f"{output_path}/Page_{i:03}", lang_str)

            output_dirs.pop()
        output_dirs.pop()

    # Output home pages
    for region in bcma.regions:
        for lang in region[1]:
            lang_str =  f"{region[0]}_{lang}"
            with open(output_dirs[0] + f"/Home_{lang_str}.html", "w", encoding="utf-8") as file:
                file.write("<!DOCTYPE html>\n")
                file.write("<html>\n")
                file.write("    <head>\n")
                file.write("        <title>bcma2html test</title>\n")
                file.write("        <meta charset=\"utf-8\">\n")
                file.write("        <link rel=\"stylesheet\" href=\"../home_page.css\">\n")
                file.write("    </head>\n")
                file.write("    <body>\n")

                file.write("        <div class=\"index\">\n")
                file.write(categories_html[lang_str])
                file.write("        </div>\n")
                
                file.write("<div style=\"position: absolute; right: 0; top: 0;\">")
                for region in bcma.regions:
                    for lang in region[1]:
                        file.write("        <a href=\"Home_{0}_{1}.html\">{0}_{1}</a>".format(region[0], lang))
                file.write("</div>")

                file.write("    </body>\n")

    print("Successfully Completed!")

main()