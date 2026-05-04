"""
テキストデータから、コンボ倍率データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv
import tomllib

from deredata.libs.database.comborates import Comborate, ComboRates

comboratedatas: ComboRates = ComboRates()
load_comboratedatas: ComboRates = ComboRates()

if __name__ == "__main__":
    with open("config/config.toml", "rb") as f:
        config = tomllib.load(f)
        TEXTDATAFOLDER: str = config["textdata_folder"]
        COMBORATEDATA: str = TEXTDATAFOLDER + "appendix_comborate.txt"

    with open(COMBORATEDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            comborate = Comborate(
                ulimit=float(data["上限"]),
                rate=float(data["コンボ倍率"]),
            )
            comboratedatas.add(comborate)

    comboratedatas.save()

    load_comboratedatas.load()

    print(f"{load_comboratedatas.rate(0.1)}")
