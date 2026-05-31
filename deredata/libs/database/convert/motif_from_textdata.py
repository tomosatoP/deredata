"""
テキストデータから、特技モチーフ効果量データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.motif import Motif, Motives

motives: Motives = Motives()

MOTIFDATA: str = textdata_folder() + "appendix_motif.txt"
MOTIFDATA_GRAND: str = textdata_folder() + "appendix_motif_grand.txt"


def main() -> None:
    with open(MOTIFDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            motif = Motif(
                appeal=int(data["アピール値"]),
                rate=float(data["倍率"]),
            )
            motives._motives.append(motif)

    with open(MOTIFDATA_GRAND, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            motif = Motif(
                appeal=int(data["アピール値"]),
                rate=float(data["倍率"]),
            )
            motives._motives_grand.append(motif)

    motives.save()


if __name__ == "__main__":
    load_motives: Motives = Motives()
    load_motives.load()

    print(load_motives.value(45000))  # 0.23
    print(load_motives.value(46000, True))  # 0.28
