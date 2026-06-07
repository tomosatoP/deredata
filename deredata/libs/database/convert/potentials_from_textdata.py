"""
テキストデータから、ポテンシャルデータベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.enumerations import RareClass
from deredata.libs.database.potentials import Appeal, Ability, Life, Potentials

potentials: Potentials = Potentials()

APPEALDATA: str = textdata_folder() + "appendix_appeals.txt"
LIFEDATA: str = textdata_folder() + "appendix_lives.txt"
ABILITYDATA: str = textdata_folder() + "appendix_abilities.txt"


def convert(
    apeals_txtfilanem: str = APPEALDATA,
    lives_txtfilename: str = LIFEDATA,
    abilities_txtfilename: str = ABILITYDATA,
    potentials_jsonfilename: str | None = None,
) -> None:

    with open(apeals_txtfilanem, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        Potentials._clear()
        appeals = [
            Appeal(rare=RareClass(data["レア度"]), level=int(column), potential=int(data[column]))
            for data in datas
            for column in data
            if column.isdecimal()
        ]
        for appeal in appeals:
            potentials.add_appeal(appeal)

    with open(abilities_txtfilename, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        abilities = [
            Ability(rare=RareClass(data["レア度"]), level=int(column), potential=float(data[column]))
            for data in datas
            for column in data
            if column.isdecimal()
        ]
        for ability in abilities:
            potentials.add_ability(ability)

    with open(lives_txtfilename, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        lives = [
            Life(rare=RareClass(data["レア度"]), level=int(column), potential=int(data[column]))
            for data in datas
            for column in data
            if column.isdecimal()
        ]
        for life in lives:
            potentials.add_life(life)

    Potentials.save(potentials_jsonfilename) if potentials_jsonfilename else Potentials.save()


if __name__ == "__main__":
    print(__file__)
    convert()
