import archive, layout


class BCMA:
    def __init__(self, data):
        self.archive = archive.DARC(data)
        self.regions, self.tex_archives = self._retrieve_info()

    def _retrieve_info(self):
        # Get BcmaInfo
        info_darc = archive.DARC(archive.decompress_lz10(self.archive.get_file("./BcmaInfo.arc")))
        info_clyt = layout.BCLYT(info_darc.get_file("./blyt/BcmaInfo.bclyt"))
        info_tree = info_clyt.layout

        # Get region/language info
        region_info = info_tree.get_user_data("RegionInfo").dict

        languages = []    
        for i in range(region_info["RegionNum"][0]):
            region_code = region_info["Region_{:03}".format(i)]
            language_info = info_tree.get_user_data(region_code).dict

            languages.append((region_code, []))
            for j in range(language_info["LangNum"][0]):
                languages[-1][1].append(language_info["Lang_{:03}".format(j)])
        
        # Get all texture archives used
        tex_arc_names = []
        for i in range(len(languages)):
            for j in range(len(languages[i][1])):
                language_code = languages[i][0] + "_" + languages[i][1][j]
                texres_info = info_tree.get_user_data(language_code).dict
                for k in range(texres_info["TexResNum"][0]):
                    archive_name = texres_info["TexRes_{:04X}".format(k)]
                    if archive_name not in tex_arc_names:
                        tex_arc_names.append(archive_name)
        
        tex_archives = []
        for name in tex_arc_names:
            tex_darc = archive.DARC(archive.decompress_lz10(self.archive.get_file("./" + name)))
            tex_archives.append(tex_darc)
        
        return region_info, tex_archives