"""
テキストデータから、特技モチーフ効果量データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv
import tomllib

import deredata.libs.database.motif as mf

motives: mf.Motives = mf.Motives()
load_motives: mf.Motives = mf.Motives()

if __name__ == "__main__":
    with open("config/config.toml", "rb") as f:
        config = tomllib.load(f)
        TEXTDATAFOLDER: str = config["textdata_folder"]
        MOTIFDATA: str = TEXTDATAFOLDER + "appendix_motif.txt"
        MOTIFDATA_GRAND: str = TEXTDATAFOLDER + "appendix_motif_grand.txt"

    with open(MOTIFDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            motif = mf.Motif(
                appeal=int(data["アピール値"]),
                rate=float(data["倍率"]),
            )
            motives._motives.append(motif)

    with open(MOTIFDATA_GRAND, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            motif = mf.Motif(
                appeal=int(data["アピール値"]),
                rate=float(data["倍率"]),
            )
            motives._motives_grand.append(motif)

    motives.save()

    load_motives.load()

    print(load_motives.value(45000))  # 0.23
    print(load_motives.value(46000, True))  # 0.28
