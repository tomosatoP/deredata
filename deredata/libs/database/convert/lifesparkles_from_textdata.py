"""
テキストデータから、特技ライフスパークル効果量データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.lifesparkles import Lifesparkle, Lifesparkles

lifesparkles: Lifesparkles = Lifesparkles()

SSRDATA: str = textdata_folder() + "appendix_lifesparkle_SSR.txt"
SRDATA: str = textdata_folder() + "appendix_lifesparkle_SR.txt"


def convert(
    lifesparkle_ssr_txtfilename: str = SSRDATA,
    lifesparkle_sr_txtfilename: str = SRDATA,
    lifesparkle_jsonfilename: str | None = None,
) -> None:

    Lifesparkles._clear()
    with open(lifesparkle_ssr_txtfilename, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            lifesparkle = Lifesparkle(
                life=int(data["残ライフ値"]),
                rate=float(data["倍率"]),
            )
            lifesparkles.add_ssr(lifesparkle)

    with open(lifesparkle_sr_txtfilename, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            lifesparkle = Lifesparkle(
                life=int(data["残ライフ値"]),
                rate=float(data["倍率"]),
            )
            lifesparkles.add_sr(lifesparkle)

    Lifesparkles.save(lifesparkle_jsonfilename) if lifesparkle_jsonfilename else Lifesparkles.save()


if __name__ == "__main__":
    print(__file__)
    convert()
