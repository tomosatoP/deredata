"""
テキストデータから、ポテンシャルデータベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.enumerations import RareClass
from deredata.libs.database.potentials import Appeal, Ability, Life, Potentials

potentials: Potentials = Potentials()
load_potentials: Potentials = Potentials()

APPEALDATA: str = textdata_folder() + "appendix_appeals.txt"
LIFEDATA: str = textdata_folder() + "appendix_lives.txt"
ABILITYDATA: str = textdata_folder() + "appendix_abilities.txt"

if __name__ == "__main__":
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
