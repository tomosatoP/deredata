"""
テキストデータから、エピソード＆フレーバーデータベース（JSONデータ）への変換を扱うモジュール。

テキストデータを固定（episodes_fixed.txt）と更新用（episodes.txt）に分割。
更新用（episodes.txt）が無い場合、パラメーターを ZERO で埋め、作成。
"""

import csv
from pathlib import Path
from setuptools._distutils.util import strtobool

from deredata.libs.database.enumerations import IdolType, DominantType, GachaType, RareClass
from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.episodes import Episode, Episodes
from deredata.libs.database.flavors import Flavor, Flavors

episodedatas = Episodes()
flavordatas = Flavors()

load_episodedatas = Episodes()
load_flavordatas = Flavors()

EPISODEFIXEDDATA: str = textdata_folder() + "episodes_fixed.txt"
EPISODEDATA: str = textdata_folder() + "episodes.txt"


if __name__ == "__main__":
    with open(EPISODEFIXEDDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            episode = Episode(
                ruby=data["ふりがな"],
                episode=data["エピソード"],
                type=IdolType(data["アイドルタイプ"]),
                dominant=DominantType(data["ドミナントアイドルタイプ"]),
                mystyle=strtobool(data["マイスタイル"]),
                rare=RareClass(data["レア度"]),
                star_rank=0,
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

    if Path(EPISODEDATA).is_file():
        with open(EPISODEDATA, "r", encoding="utf-8-sig") as f:
            datas = csv.DictReader(f)

            for data in datas:
                episode_fixed = episodedatas.get(data["エピソード"])
                episode = Episode(
                    ruby=episode_fixed.ruby,
                    episode=data["エピソード"],
                    type=episode_fixed.type,
                    dominant=episode_fixed.dominant,
                    mystyle=episode_fixed.mystyle,
                    rare=episode_fixed.rare,
                    star_rank=int(data["スターランク"]),
                    skill_level=episode_fixed.skill_level,
                    level=episode_fixed.level,
                    affection=episode_fixed.affection,
                    vocal=episode_fixed.vocal,
                    dance=episode_fixed.dance,
                    visual=episode_fixed.visual,
                    life=episode_fixed.life,
                    buff_class=episode_fixed.buff_class,
                    buff=episode_fixed.buff,
                    skill_class=episode_fixed.skill_class,
                    skill=episode_fixed.skill,
                )
                episodedatas.update(after=episode, before=episode_fixed)

    else:
        with open(EPISODEDATA, "w", encoding="utf-8-sig", newline="") as f:
            fieldnames: list[str] = ["エピソード", "スターランク"]
            writer = csv.DictWriter(f=f, fieldnames=fieldnames)

            writer.writeheader()
            for episode in sorted(episodedatas.gets()):
                writer.writerow(
                    {
                        "エピソード": episode.episode,
                        "スターランク": str(episode.star_rank),
                    }
                )

    episodedatas.save()
    flavordatas.save()

    load_episodedatas.load()
    load_flavordatas.load()

    print(load_episodedatas.get("［キャッチミー・オールタイム］島村卯月＋"))
    print(load_flavordatas.get("［キャッチミー・オールタイム］島村卯月＋"))
