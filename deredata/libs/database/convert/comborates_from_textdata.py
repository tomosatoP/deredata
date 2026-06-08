"""
テキストデータから、コンボ倍率データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.comborates import Comborate, ComboRates

comboratedatas: ComboRates = ComboRates()

COMBORATEDATA: str = textdata_folder() + "appendix_comborate.txt"


def convert(
    comborate_txtfilename: str = COMBORATEDATA,
    comborate_jsonfilename: str | None = None,
) -> None:

    ComboRates._clear()
    with open(comborate_txtfilename, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            comborate = Comborate(
                ulimit=float(data["上限"]),
                rate=float(data["コンボ倍率"]),
            )
            comboratedatas.add(comborate)

    ComboRates.save(comborate_jsonfilename) if comborate_jsonfilename else ComboRates.save()


if __name__ == "__main__":
    print(__file__)
    convert()
