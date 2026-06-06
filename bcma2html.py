import struct, sys, os, argparse
import archive, texture, layout
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
            self.add_raw(f"<div class=\"{css_class}\"")
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
        with open(self.path, "w", encoding="utf-8") as file:
            file.write("<!DOCTYPE html>\n")
            file.write("<html>\n")
            file.write("\t<head>\n")
            file.write("\t\t<title>bcma2html test</title>\n")
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
        if self.selectors[class_name] is None:
            self.selectors[class_name] = []
        
        self.selectors[class_name] += f"{name}: {value};"
    
    def write(self):
        with open(self.path, "w", encoding="utf-8") as file:
            for props in self.selectors.items():
                file.write(f"{props[0]} {{\n")
                for property in props[1]:
                    file.write(f"\t{property}\n")
                file.write("}")

def export(trees, tex_archives, path, region_lang):
    css_name = os.path.basename(path)
    with open(f"{path}.html", "w", encoding="utf-8") as html_file, open(f"{path}.css", "w", encoding="utf-8") as css_file:
        css_file.write("body, div, p {\n")
        css_file.write("    margin: 0;\n")
        css_file.write("    padding: 0;\n")
        css_file.write("    box-sizing: border-box;\n")
        css_file.write("}\n")

        css_file.write("body {\n")
        css_file.write("    display: flex;\n")
        css_file.write("    justify-content: center;\n")
        css_file.write("}\n")

        css_file.write(".manual {\n")
        css_file.write("    position: relative;\n")
        css_file.write("    width: {}px;\n".format(trees[0].canvas_size[0]))
        css_file.write("    height: {}px;\n".format(trees[0].canvas_size[1]))
        css_file.write("    white-space: preserve nowrap;\n")
        css_file.write("}\n")

        html_file.write("<!DOCTYPE html>\n")
        html_file.write("<html>\n")
        html_file.write("    <head>\n")
        html_file.write("        <title>bcma2html test</title>\n")
        html_file.write("        <meta charset=\"utf-8\">\n")
        html_file.write(f"        <link rel=\"stylesheet\" href=\"{css_name}.css\">\n")
        html_file.write("    </head>\n")
        html_file.write("    <body>\n")

        html_file.write("       <a href=\"../../Home_{}.html\" style=\"position: absolute; left: {}px;\">Home</a>\n".format(region_lang, trees[0].canvas_size[0]))

        html_file.write("       <div class=\"manual\">\n")
        for tree in trees:
            convert(tree, tex_archives, tree, path, html_file, css_file)
        html_file.write("       </div>\n")

        html_file.write("    </body>\n")
        html_file.write("</html>\n")
    
    split = 0
    for tree in trees:
        with open(f"{path}_{split:03}.txt", "w", encoding="utf-8") as text_file:
            convert_txt(tree, text_file)
        split += 1

def convert(tree, tex_archives, node, path: str, html_file, css_file):
    if type(node) == layout.Pane:
        html_file.write("<div class=\"{}\">\n".format(node.name))

        css_file.write(".{} {{\n".format(node.name))
        css_file.write("    position: absolute;\n")
        css_file.write("    left: {}px;\n".format(node.pane_data.translation[0]))
        css_file.write("    top: {}px;\n".format(-node.pane_data.translation[1]))
        css_file.write("    width: {}px;\n".format(node.pane_data.size[0]))
        css_file.write("    height: {}px;\n".format(node.pane_data.size[1]))
        css_file.write("}\n")

    # if type(node) == Canvas or type(node) == Pane:
    if type(node) == layout.LayoutTree or type(node) == layout.Pane:
        for child in node.children:
            convert(tree, tex_archives, child, path, html_file, css_file)
    elif type(node) == layout.Text:
        html_file.write("<p class=\"{}\">{}</p>\n".format(node.name, node.text))

        css_file.write(".{} {{\n".format(node.name))
        css_file.write("    position: absolute;\n")
        css_file.write("    left: {}px;\n".format(node.pane_data.translation[0]))
        css_file.write("    top: {}px;\n".format(-node.pane_data.translation[1]))
        css_file.write("    width: {}px;\n".format(node.pane_data.size[0]))
        css_file.write("    height: {}px;\n".format(node.pane_data.size[1]))
        css_file.write("    font-size: {}px;\n".format(node.font_scale[1]))
        css_file.write("    color: #{:08X};\n".format(struct.unpack("<I", struct.pack(">I", node.top_color))[0]))
        css_file.write("}\n")
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

        html_file.write("<img src=\"{}\" class=\"{}\">".format(tex_name.replace(".bclim", ".png"), node.name))

        css_file.write(".{} {{\n".format(node.name))
        css_file.write("    position: absolute;\n")
        css_file.write("    left: {}px;\n".format(node.pane_data.translation[0]))
        css_file.write("    top: {}px;\n".format(-node.pane_data.translation[1]))
        css_file.write("    width: {}px;\n".format(node.pane_data.size[0]))
        css_file.write("    height: {}px;\n".format(node.pane_data.size[1]))
        css_file.write("}\n")

        for darc in tex_archives:
            if darc.has_file("./timg/" + tex_name):
                bclim = texture.BCLIM(darc.get_file("./timg/" + tex_name))
                bclim.save_as_png(path[:path.rfind('/')] + "/" + tex_name.replace(".bclim", ".png"))
    elif type(node) == layout.Window:
        mat_list = tree.get_toplevel_obj_of_type(layout.MaterialList)
        tex_list = tree.get_toplevel_obj_of_type(layout.TextureList)
        assert mat_list is not None, "Material list missing!"
        
        mat_index = node.cont_data[4]
        tex_index = mat_list.materials[mat_index][1]

        node.load_texture_sizes(mat_list, tex_list, tex_archives)
        css_file.write(".{} {{\n".format(node.name))
        css_file.write("    position: absolute;\n")
        css_file.write("    left: {}px;\n".format(node.pane_data.translation[0]))
        css_file.write("    top: {}px;\n".format(-node.pane_data.translation[1]))
        css_file.write("    width: {}px;\n".format(node.content_box[1] - node.content_box[0]))
        css_file.write("    height: {}px;\n".format(node.content_box[3] - node.content_box[2]))
        css_file.write("    background-color: #{:08X};\n".format(struct.unpack("<I", struct.pack(">I", node.cont_data[0]))[0]))

        if node.border_image is not None:
            css_file.write("    border: solid transparent;")
            css_file.write("    border-left-width: {}px;\n".format(node.content_box[0]))
            css_file.write("    border-right-width: {}px;\n".format(node.pane_data.size[0] - node.content_box[1]))
            css_file.write("    border-top-width: {}px;\n".format(node.content_box[2]))
            css_file.write("    border-bottom-width: {}px;\n".format(node.pane_data.size[1] - node.content_box[3]))
            css_file.write("    border-image: url(\"{}\");\n".format(path[path.rfind('/') + 1:] + "_" + node.name + ".png"))
            css_file.write("    border-image-slice: {} {} {} {};\n".format(node.content_box[2], node.content_box[0], node.pane_data.size[1] - node.content_box[3], node.pane_data.size[0] - node.content_box[1]))
            css_file.write("    box-sizing: content-box;")
            css_file.write("    background-clip: padding-box;")
        
        if len(tex_index) == 1:
            assert tex_list is not None, "Texture list missing!"
            tex_name: str = tex_list.textures[tex_index[0][0]]
            css_file.write("background-image: url(\"{}\");".format(tex_name.replace(".bclim", ".png")))
            for darc in tex_archives:
                if darc.has_file("./timg/" + tex_name):
                    bclim = texture.BCLIM(darc.get_file("./timg/" + tex_name))
                    bclim.save_as_png(path[:path.rfind('/')] + "/" + tex_name.replace(".bclim", ".png"))

        css_file.write("}\n")
        html_file.write("<div class=\"{}\"></div>".format(node.name))

        if node.border_image is not None:
            export = PIL.Image.new("RGBA", node.border_image_size)
            export.frombytes(bytes(node.border_image))
            export.save(path + "_" + node.name + ".png", format="png")

    if type(node) == layout.Pane:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("manual", help="Path to the BCMA file (usually Manual.bcma)")
    args = parser.parse_args()

    bcma_path = args.manual
    root_path = os.path.dirname(sys.argv[0])

    # Index the .bcma
    bcma_darc = None
    with open(bcma_path, "rb") as file:
        bcma_darc = archive.DARC(file.read())

    # Get BcmaInfo
    info_darc = archive.DARC(archive.decompress_lz10(bcma_darc.get_file("./BcmaInfo.arc")))
    info_clyt = layout.BCLYT(info_darc.get_file("./blyt/BcmaInfo.bclyt"))
    info_tree = info_clyt.layout
    
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
    
    tex_arc_names = []
    for i in range(len(languages)):
        for j in range(len(languages[i][1])):
            language_code = languages[i][0] + "_" + languages[i][1][j]
            texres_info = info_tree.get_user_data(language_code)
            for k in range(texres_info.dict["TexResNum"][0]):
                archive_name = texres_info.dict["TexRes_{:04X}".format(k)]
                if archive_name not in tex_arc_names:
                    tex_arc_names.append(archive_name)
    
    tex_archives = []
    for name in tex_arc_names:
        tex_darc = archive.DARC(archive.decompress_lz10(bcma_darc.get_file("./" + name)))
        tex_archives.append(tex_darc)

    # Parse and convert each language
    categories_html = {}
    page_num = {}
    output_dirs = [f"{root_path}/output"]
    for region in languages:
        output_dirs.append(region[0])
        for lang in region[1]:
            output_dirs.append(lang)
            
            if not os.path.exists(fold_dirs(output_dirs)):
                os.makedirs(fold_dirs(output_dirs))

            # Get Index.bclyt
            index_darc = archive.DARC(archive.decompress_lz10(bcma_darc.get_file(f"./{region[0]}_{lang}_index.arc")))
            index_clyt = layout.BCLYT(index_darc.get_file("./blyt/Index.bclyt"))
            index_tree = index_clyt.layout

            # Get metadata
            metadata = index_tree.get_user_data("MetaData")
            assert(metadata is not None)

            # Get page titles
            titles = []
            for i in range(metadata.dict["PageNum"][0]):
                page_title = index_tree.get_named_obj(f"PageTitle_{i:03}")
                assert(page_title is not None)
                titles.append(page_title.text)
                page_num[f"{region[0]}_{lang}"] = metadata.dict["PageNum"][0]
                
            # Get categories
            categories = []
            for i in range(metadata.dict["CategoryNum"][0]):
                category = index_tree.get_user_data(f"Category_{i:03}")
                category_title = index_tree.get_named_obj(f"Category_{i:03}")
                category_pages = []
                for j in range(category.dict["CategoryPageNum"][0]):
                    category_pages.append(category.dict[f"PageID_{j:03}"][0])

                categories.append((category_title.text, category.dict["IsValid"][0] == 1, category_pages))

            # Make HTML for home page category links
            category_html = "<p>{}_{}</p>".format(region[0], lang)
            for category in categories:
                if category[1]:
                    category_html += "<p>{}</p>".format(category[0])
                
                for page in category[2]:
                    category_html += "<a href=\"{}/{}/Page_{:03}.html\">{}</a><br>".format(region[0], lang, page, titles[page])
            category_html += "<br>"
            categories_html[f"{region[0]}_{lang}"] = category_html

            # Convert each page (small ones for now)
            for i, splits in enumerate(metadata.dict["SplitNumS"]):
                page_darc = archive.DARC(archive.decompress_lz10(bcma_darc.get_file(f"./{region[0]}_{lang}_small.arc")))
                page_trees = []

                # Background
                page_file = page_darc.get_file(f"./blyt/Page_{i:03}_small_bg.bclyt")
                page_trees.append(layout.BCLYT(page_file).layout)
                
                for split in range(splits):
                    page_file = page_darc.get_file(f"./blyt/Page_{i:03}_small_{split}.bclyt")
                    page_trees.append(layout.BCLYT(page_file).layout)
                
                output_path = fold_dirs(output_dirs)
                export(page_trees, tex_archives, f"{output_path}/Page_{i:03}", f"{region[0]}_{lang}")

            output_dirs.pop()
        output_dirs.pop()

    # Output home pages
    for region in languages:
        for lang in region[1]:
            with open(output_dirs[0] + f"/Home_{region[0]}_{lang}.html", "w", encoding="utf-8") as file:
                file.write("<!DOCTYPE html>\n")
                file.write("<html>\n")
                file.write("    <head>\n")
                file.write("        <title>bcma2html test</title>\n")
                file.write("        <meta charset=\"utf-8\">\n")
                # file.write(f"        <link rel=\"stylesheet\" href=\"{css_name}.css\">\n")
                file.write("    </head>\n")
                file.write("    <body>\n")

                file.write(categories_html[f"{region[0]}_{lang}"])
                
                file.write("<div style=\"position: absolute; right: 0; top: 0;\">")
                for region in languages:
                    for lang in region[1]:
                        file.write("        <a href=\"Home_{0}_{1}.html\">{0}_{1}</a>".format(region[0], lang))
                file.write("</div>")

                file.write("    </body>\n")

    print("Successfully Completed!")


main()