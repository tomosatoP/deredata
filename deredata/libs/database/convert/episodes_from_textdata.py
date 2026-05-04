"""
テキストデータから、エピソード＆フレーバーデータベース（JSONデータ）への変換を扱うモジュール。
"""

import csv
import tomllib
from setuptools._distutils.util import strtobool

from deredata.libs.database import enums
from deredata.libs.database import episodes
from deredata.libs.database import flavors

episodedatas = episodes.Episodes()
flavordatas = flavors.Flavors()
load_episodedatas = episodes.Episodes()
load_flavordatas = flavors.Flavors()

if __name__ == "__main__":
    with open("config/config.toml", "rb") as f:
        config = tomllib.load(f)
        TEXTDATAFOLDER: str = config["textdata_folder"]
        EPISODEDATA: str = TEXTDATAFOLDER + "episodes.txt"

    with open(EPISODEDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            episode = episodes.Episode(
                ruby=data["ふりがな"],
                episode=data["エピソード"],
                type=enums.IdolType(data["アイドルタイプ"]),
                dominant=enums.DominantType(data["ドミナントアイドルタイプ"]),
                mystyle=strtobool(data["マイスタイル"]),
                rare=enums.RareClass(data["レア度"]),
                star_rank=int(data["スターランク"]),
                skill_level=int(data["特技レベル"]),
                level=int(data["レベル"]),
                affection=int(data["親愛度"]),
                vocal=int(data["ボーカル"]),
                dance=int(data["ダンス"]),
                visual=int(data["ビジュアル"]),
                life=int(data["ライフ"]),
                buff_class=data["センター効果"],
                buff=data["センター効果説明"],
                skill_class=data["特技"],
                skill=data["特技説明"],
            )
            flavor = flavors.Flavor(
                episode=data["エピソード"],
                voice=strtobool(data["ボイス"]),
                solo=strtobool(data["ソロ"]),
                gacha=enums.GachaType(data["入手枠"]),
                registration_date=data["登録日"].strip("'"),
            )

            episodedatas.add(episode)
            flavordatas.add(flavor)

    episodedatas.save()
    flavordatas.save()

    load_episodedatas.load()
    load_flavordatas.load()

    print(load_episodedatas.get("［キャッチミー・オールタイム］島村卯月＋"))
    print(load_flavordatas.get("［キャッチミー・オールタイム］島村卯月＋"))
