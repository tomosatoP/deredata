"""
テキストデータから、特技ドミナント・ハーモニー効果量データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.dominants import Dominant, Dominants

dominants: Dominants = Dominants()

GUESTDATA: str = textdata_folder() + "appendix_dominant_guest.txt"
NOGUESTDATA: str = textdata_folder() + "appendix_dominant_noguest.txt"


def convert(
    dominant_guest_txtfilename: str = GUESTDATA,
    dominant_noguest_txtfilename: str = NOGUESTDATA,
    dominant_jsonfilename: str | None = None,
) -> None:

    Dominants._clear()
    with open(dominant_guest_txtfilename, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            dominant = Dominant(
                number=int(data["編成人数"]),
                score=float(data["スコアボーナス"]),
                combo=float(data["COMBOボーナス"]),
            )
            dominants.add_with_guest(dominant)

    with open(dominant_noguest_txtfilename, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            dominant = Dominant(
                number=int(data["編成人数"]),
                score=float(data["スコアボーナス"]),
                combo=float(data["COMBOボーナス"]),
            )
            dominants.add_without_guest(dominant)

    Dominants.save(dominant_jsonfilename) if dominant_jsonfilename else Dominants.save()


if __name__ == "__main__":
    print(__file__)
    convert()
