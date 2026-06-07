"""
テキストデータから、曲係数データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.musiclevels import MusicLevel, MusicLevels

musicleveldatas: MusicLevels = MusicLevels()

MUSICLEVELDATA: str = textdata_folder() + "appendix_musiclevel.txt"


def convert(
    musiclevels_txtfilename: str = MUSICLEVELDATA,
    musiclevels_jsonfilename: str | None = None,
) -> None:

    MusicLevels._clear()
    with open(MUSICLEVELDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            musiclevel = MusicLevel(
                level=int(data["楽曲Lv"]),
                rate=float(data["曲係数"]),
            )
            musicleveldatas.add(musiclevel)

    MusicLevels.save(musiclevels_jsonfilename) if musiclevels_jsonfilename else MusicLevels.save()


if __name__ == "__main__":
    print(__file__)
    convert()
