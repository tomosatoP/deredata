"""
テキストデータから、曲係数データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv
import tomllib

from deredata.libs.database.musiclevels import MusicLevel, MusicLevels

musicleveldatas: MusicLevels = MusicLevels()
load_musicleveldatas: MusicLevels = MusicLevels()

if __name__ == "__main__":
    with open("config/config.toml", "rb") as f:
        config = tomllib.load(f)
        TEXTDATAFOLDER: str = config["textdata_folder"]
        MUSICLEVELDATA: str = TEXTDATAFOLDER + "appendix_musiclevel.txt"

    with open(MUSICLEVELDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            musiclevel = MusicLevel(
                level=int(data["楽曲Lv"]),
                rate=float(data["曲係数"]),
            )
            musicleveldatas.add(musiclevel)

    musicleveldatas.save()

    load_musicleveldatas.load()

    print(f"{load_musicleveldatas.rate(31)}")  # 2.3
