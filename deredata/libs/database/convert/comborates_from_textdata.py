"""
テキストデータから、コンボ倍率データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.comborates import Comborate, ComboRates

comboratedatas: ComboRates = ComboRates()

COMBORATEDATA: str = textdata_folder() + "appendix_comborate.txt"


def main() -> None:
    with open(COMBORATEDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            comborate = Comborate(
                ulimit=float(data["上限"]),
                rate=float(data["コンボ倍率"]),
            )
            comboratedatas.add(comborate)

    comboratedatas.save()


if __name__ == "__main__":
    load_comboratedatas: ComboRates = ComboRates()
    load_comboratedatas.load()

    print(f"{load_comboratedatas.rate(0.1)}")
