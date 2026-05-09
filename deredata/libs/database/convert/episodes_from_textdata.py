"""
テキストデータから、エピソード＆フレーバーデータベース（JSONデータ）への変換を扱うモジュール。
"""

import csv
from setuptools._distutils.util import strtobool

from deredata.libs.database.enumerations import IdolType, DominantType, GachaType, RareClass
from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.episodes import Episode, Episodes
from deredata.libs.database.flavors import Flavor, Flavors

episodedatas = Episodes()
flavordatas = Flavors()

load_episodedatas = Episodes()
load_flavordatas = Flavors()

EPISODEDATA: str = textdata_folder() + "episodes.txt"


if __name__ == "__main__":
    with open(EPISODEDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            episode = Episode(
                ruby=data["ふりがな"],
                episode=data["エピソード"],
                type=IdolType(data["アイドルタイプ"]),
                dominant=DominantType(data["ドミナントアイドルタイプ"]),
                mystyle=strtobool(data["マイスタイル"]),
                rare=RareClass(data["レア度"]),
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
            flavor = Flavor(
                episode=data["エピソード"],
                voice=strtobool(data["ボイス"]),
                solo=strtobool(data["ソロ"]),
                gacha=GachaType(data["入手枠"]),
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
