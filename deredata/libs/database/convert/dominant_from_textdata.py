"""
テキストデータから、特技ドミナント・ハーモニー効果量データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.dominant import Dominant, Dominants

dominants: Dominants = Dominants()

GUESTDATA: str = textdata_folder() + "appendix_dominant_guest.txt"
NOGUESTDATA: str = textdata_folder() + "appendix_dominant_noguest.txt"


def main() -> None:
    with open(GUESTDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            dominant = Dominant(
                number=int(data["編成人数"]),
                score=float(data["スコアボーナス"]),
                combo=float(data["COMBOボーナス"]),
            )
            dominants._dominants_guest.append(dominant)

    with open(NOGUESTDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            dominant = Dominant(
                number=int(data["編成人数"]),
                score=float(data["スコアボーナス"]),
                combo=float(data["COMBOボーナス"]),
            )
            dominants._dominants_noguest.append(dominant)

    dominants.save()


if __name__ == "__main__":
    load_dominants: Dominants = Dominants()
    load_dominants.load()

    print(load_dominants.value(2, 0))  # 0.2
    print(load_dominants.value(2, 1))  # 0.25
    print(load_dominants.value(2, 0, False))  # 0.3
