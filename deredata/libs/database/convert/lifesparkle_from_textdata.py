"""
テキストデータから、特技ライフスパークル効果量データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv
import tomllib

import deredata.libs.database.lifesparkle as ls

lifesparkles: ls.Lifesparkles = ls.Lifesparkles()
load_lifesparkles: ls.Lifesparkles = ls.Lifesparkles()

if __name__ == "__main__":
    with open("config/config.toml", "rb") as f:
        config = tomllib.load(f)
        TEXTDATAFOLDER: str = config["textdata_folder"]
        SSRDATA: str = TEXTDATAFOLDER + "appendix_lifesparkle_SSR.txt"
        SRDATA: str = TEXTDATAFOLDER + "appendix_lifesparkle_SR.txt"

    with open(SSRDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            lifesparkle = ls.Lifesparkle(
                life=int(data["残ライフ値"]),
                rate=float(data["倍率"]),
            )
            lifesparkles._lifesparkles_ssr.append(lifesparkle)

    with open(SRDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            lifesparkle = ls.Lifesparkle(
                life=int(data["残ライフ値"]),
                rate=float(data["倍率"]),
            )
            lifesparkles._lifesparkles_sr.append(lifesparkle)

    lifesparkles.save()

    load_lifesparkles.load()

    print(load_lifesparkles.value(1000))  # 0.29
    print(load_lifesparkles.value(0))  # 0.09
    print(load_lifesparkles.value(1000, "SR"))  # 0.25
