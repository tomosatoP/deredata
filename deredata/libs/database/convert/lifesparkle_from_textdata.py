"""
テキストデータから、特技ライフスパークル効果量データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.lifesparkle import Lifesparkle, Lifesparkles

lifesparkles: Lifesparkles = Lifesparkles()
load_lifesparkles: Lifesparkles = Lifesparkles()

SSRDATA: str = textdata_folder() + "appendix_lifesparkle_SSR.txt"
SRDATA: str = textdata_folder() + "appendix_lifesparkle_SR.txt"

if __name__ == "__main__":
    with open(SSRDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            lifesparkle = Lifesparkle(
                life=int(data["残ライフ値"]),
                rate=float(data["倍率"]),
            )
            lifesparkles._lifesparkles_ssr.append(lifesparkle)

    with open(SRDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            lifesparkle = Lifesparkle(
                life=int(data["残ライフ値"]),
                rate=float(data["倍率"]),
            )
            lifesparkles._lifesparkles_sr.append(lifesparkle)

    lifesparkles.save()

    load_lifesparkles.load()

    print(load_lifesparkles.value(1000))  # 0.29
    print(load_lifesparkles.value(0))  # 0.09
    print(load_lifesparkles.value(1000, "SR"))  # 0.25
