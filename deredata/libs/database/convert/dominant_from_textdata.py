"""
テキストデータから、特技ドミナント・ハーモニー効果量データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv
import tomllib

import deredata.libs.database.dominant as dm

dominants: dm.Dominants = dm.Dominants()
load_dominants: dm.Dominants = dm.Dominants()

if __name__ == "__main__":
    with open("config/config.toml", "rb") as f:
        config = tomllib.load(f)
        TEXTDATAFOLDER: str = config["textdata_folder"]
        GUESTDATA: str = TEXTDATAFOLDER + "appendix_dominant_guest.txt"
        NOGUESTDATA: str = TEXTDATAFOLDER + "appendix_dominant_noguest.txt"

    with open(GUESTDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            dominant = dm.Dominant(
                number=int(data["編成人数"]),
                score=float(data["スコアボーナス"]),
                combo=float(data["COMBOボーナス"]),
            )
            dominants._dominants_guest.append(dominant)

    with open(NOGUESTDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            dominant = dm.Dominant(
                number=int(data["編成人数"]),
                score=float(data["スコアボーナス"]),
                combo=float(data["COMBOボーナス"]),
            )
            dominants._dominants_noguest.append(dominant)

    dominants.save()

    load_dominants.load()

    print(load_dominants.value(2, 0))  # 0.2
    print(load_dominants.value(2, 1))  # 0.25
    print(load_dominants.value(2, 0, False))  # 0.3
