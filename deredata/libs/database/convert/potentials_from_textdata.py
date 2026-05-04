"""
テキストデータから、ポテンシャルデータベース（JSONデータ）への変換を扱うモジュール。
"""

import csv
import tomllib

from deredata.libs.database.enums import RareClass
from deredata.libs.database.potentials import Appeal, Ability, Life, Potentials

potentials: Potentials = Potentials()
load_potentials: Potentials = Potentials()

if __name__ == "__main__":
    with open("config/config.toml", "rb") as f:
        config = tomllib.load(f)
        TEXTDATAFOLDER: str = config["textdata_folder"]
        APPEALDATA: str = TEXTDATAFOLDER + "appendix_appeals.txt"
        LIFEDATA: str = TEXTDATAFOLDER + "appendix_lives.txt"
        ABILITYDATA: str = TEXTDATAFOLDER + "appendix_abilities.txt"

    with open(APPEALDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        potentials._appeals = [
            Appeal(rare=RareClass(data["レア度"]), level=int(column), potential=int(data[column]))
            for data in datas
            for column in data
            if column.isdecimal()
        ]

    with open(ABILITYDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        potentials._abilities = [
            Ability(rare=RareClass(data["レア度"]), level=int(column), potential=float(data[column]))
            for data in datas
            for column in data
            if column.isdecimal()
        ]

    with open(LIFEDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        potentials._lives = [
            Life(rare=RareClass(data["レア度"]), level=int(column), potential=int(data[column]))
            for data in datas
            for column in data
            if column.isdecimal()
        ]

    potentials.save()

    load_potentials.load()

    print(load_potentials.value("ボーカル", RareClass.SSR, 10))  # 500
    print(load_potentials.value("特技発動率", RareClass.SSR, 10))  # 0.2
    print(load_potentials.value("ライフ", RareClass.SSR, 10))  # 22
