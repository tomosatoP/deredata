"""
テキストデータから、特技モチーフ効果量データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.motives import Motif, Motives

motives: Motives = Motives()

MOTIFDATA: str = textdata_folder() + "appendix_motif.txt"
MOTIFDATA_GRAND: str = textdata_folder() + "appendix_motif_grand.txt"


def convert(
    motives_txtfilenam: str = MOTIFDATA,
    motives_grand_txtfilename: str = MOTIFDATA_GRAND,
    motives_jsonfilename: str | None = None,
) -> None:

    Motives._clear()
    with open(motives_txtfilenam, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            motif = Motif(
                appeal=int(data["アピール値"]),
                rate=float(data["倍率"]),
            )
            motives.add_motif(motif)

    with open(motives_grand_txtfilename, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            motif = Motif(
                appeal=int(data["アピール値"]),
                rate=float(data["倍率"]),
            )
            motives.add_motif_grand(motif)

    Motives.save(motives_jsonfilename) if motives_jsonfilename else Motives.save()


if __name__ == "__main__":
    print(__file__)
    convert()
