import archive, texture, layout


class BCMA:
    def __init__(self, data: bytes):
        self.archive = archive.DARC(data)
        self.regions, self.tex_archives = self._retrieve_info()
        self.indices = self._retrieve_indices()
        self.page_archives = self._get_page_archives()
    
    def _retrieve_info(self):
        # Get BcmaInfo.bclyt
        info_darc = archive.DARC(archive.decompress_lz10(self.archive.get_file("./BcmaInfo.arc")))
        info_tree = layout.BCLYT(info_darc.get_file("./blyt/BcmaInfo.bclyt")).layout

        # Get region/language info
        region_info = info_tree.get_user_data("RegionInfo").dict
        languages: list[tuple[str, list[str]]] = []    
        for i in range(region_info["RegionNum"][0]):
            region_code: str = region_info["Region_{:03}".format(i)]
            language_info = info_tree.get_user_data(region_code).dict

            languages.append((region_code, []))
            for j in range(language_info["LangNum"][0]):
                languages[-1][1].append(language_info["Lang_{:03}".format(j)])
        
        # Get all texture archives used
        tex_arc_names: list[str] = []
        for i in range(len(languages)):
            for j in range(len(languages[i][1])):
                language_code = languages[i][0] + "_" + languages[i][1][j]
                texres_info = info_tree.get_user_data(language_code).dict
                for k in range(texres_info["TexResNum"][0]):
                    archive_name = texres_info["TexRes_{:04X}".format(k)]
                    if archive_name not in tex_arc_names:
                        tex_arc_names.append(archive_name)
        
        tex_archives: list[archive.DARC] = []
        for name in tex_arc_names:
            tex_darc = archive.DARC(archive.decompress_lz10(self.archive.get_file("./" + name)))
            tex_archives.append(tex_darc)
        
        return languages, tex_archives
    
    def _retrieve_indices(self):
        indices: dict[str, tuple[list[tuple[str, bool, list[int]]], list[tuple[list[str], list[int], list[int]]]]] = {}
        for region in self.regions:
            for lang in region[1]:
                # Get Index.bclyt
                index_darc = archive.DARC(archive.decompress_lz10(self.archive.get_file(f"./{region[0]}_{lang}_index.arc")))
                index_tree = layout.BCLYT(index_darc.get_file("./blyt/Index.bclyt")).layout
                metadata = index_tree.get_user_data("MetaData").dict

                # Get page titles
                titles: list[str] = []
                for i in range(metadata["PageNum"][0]):
                    page_title: layout.Text = index_tree.get_named_obj(f"PageTitle_{i:03}")
                    titles.append(page_title.text)
                    
                # Get categories
                categories: list[tuple[str, bool, list[int]]] = []
                for i in range(metadata["CategoryNum"][0]):
                    category = index_tree.get_user_data(f"Category_{i:03}").dict
                    category_title: layout.Text = index_tree.get_named_obj(f"Category_{i:03}")
                    category_pages: list[int] = []
                    for j in range(category["CategoryPageNum"][0]):
                        category_pages.append(category[f"PageID_{j:03}"][0])

                    categories.append((category_title.text, category["IsValid"][0] == 1, category_pages))
                
                # Get splits
                splits_s: list[int] = metadata["SplitNumS"]
                splits_l: list[int] = metadata["SplitNumL"]
                assert len(splits_s) == len(splits_l) == len(titles), f"Page counts mismatch in {region[0]}_{lang} index!"

                # Pack into single tuple per language
                indices[f"{region[0]}_{lang}"] = (categories, [(titles[i], splits_s[i], splits_l[i]) for i in range(len(titles))])

        return indices

    def _get_page_archives(self):
        page_archives = {}
        for region in self.regions:
            for lang in region[1]:
                darc_s = archive.DARC(archive.decompress_lz10(self.archive.get_file(f"./{region[0]}_{lang}_small.arc")))
                darc_l = archive.DARC(archive.decompress_lz10(self.archive.get_file(f"./{region[0]}_{lang}_large.arc")))
                page_archives[f"{region[0]}_{lang}"] = (darc_s, darc_l)
        
        return page_archives

    def get_bcmainfo(self):
        if not self.archive.has_file("./BcmaInfo.arc"):
            return None

        info_darc = archive.DARC(archive.decompress_lz10(self.archive.get_file("./BcmaInfo.arc")))
        return layout.BCLYT(info_darc.get_file("./blyt/BcmaInfo.bclyt"))

    def get_index(self, lang_str: str):
        if not self.archive.has_file(f"./{lang_str}_index.arc"):
            return None

        index_darc = archive.DARC(archive.decompress_lz10(self.archive.get_file(f"./{lang_str}_index.arc")))
        return layout.BCLYT(index_darc.get_file("./blyt/Index.bclyt"))

    def get_categories(self, lang_str: str):
        if lang_str not in self.indices:
            return None
        
        return self.indices[lang_str][0]

    def get_page_count(self, lang_str: str):
        if lang_str not in self.indices:
            return None
        
        return len(self.indices[lang_str][1])

    def get_page_title(self, lang_str: str, index: int):
        if lang_str not in self.indices:
            return None
        
        return self.indices[lang_str][1][index][0]

    def get_page_splits(self, lang_str: str, index: int, large: bool = False):
        if lang_str not in self.indices:
            return None
        
        return self.indices[lang_str][1][index][2] if large else self.indices[lang_str][1][index][1]

    def _get_page_file(self, lang_str: str, file_str: str, large: bool = False):
        if lang_str not in self.page_archives:
            return None

        if not self.page_archives[lang_str][int(large)].has_file(file_str):
            return None

        return layout.BCLYT(self.page_archives[lang_str][int(large)].get_file(file_str))

    def get_page_bg(self, lang_str: str, index: int, large: bool = False):
        file_str = f"./blyt/Page_{index:03}_{"large" if large else "small"}_bg.bclyt"
        return self._get_page_file(lang_str, file_str, large)

    def get_page_info(self, lang_str: str, index: int, large: bool = False):
        file_str = f"./blyt/Page_{index:03}_{"large" if large else "small"}_info.bclyt"
        return self._get_page_file(lang_str, file_str, large)
    
    def get_page_split(self, lang_str: str, index: int, split: int, large: bool = False):
        file_str = f"./blyt/Page_{index:03}_{"large" if large else "small"}_{split}.bclyt"
        return self._get_page_file(lang_str, file_str, large)

    def get_texture(self, name: str):
        for darc in self.tex_archives:
            if darc.has_file("./timg/" + name):
                return texture.BCLIM(darc.get_file("./timg/" + name))
        
        return None