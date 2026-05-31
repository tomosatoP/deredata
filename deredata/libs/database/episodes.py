"""
エピソードを扱うモジュール。

エピソードは、［エピソード名］により特徴づけられたアイドルのライブスタイルで、スコア計算に用いる。

:dataclass Episode: エピソードの基本情報（エピソード名、各アピール値など）。
:class Episodes: エピソードの基本情報データベース。
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from setuptools._distutils.util import strtobool

from deredata.libs.database.enumerations import IdolType, DominantType, RareClass
from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsEpisodesLogger

EPISODESDB: str = database_folder() + "episodes.json"


class EpisodesError(Exception):
    """epsodesのエラーハンドラ"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsEpisodesLogger.error(f"EpisodesError: {args}")


@dataclass(order=True, frozen=True)
class Episode:
    """
    エピソードの基本情報。

    :param str ruby: ふりがな（アクセスキー）
    :param str episode: エピソード名（アクセスキー）
    :param enums.IdolType type: アイドルタイプ
    :param enums.DominantTyp dominant: ドミナントアイドルタイプ
    :param bool mystyle: ``True`` ならマイスタイルアイドル
    :param enums.RareClass rare: レア度（特訓後）
    :param int star_rank: スターランク
    :param int skill_level: 特技レベル（最大値）
    :param int level: レベル（最大値）
    :param int life: 基礎ライフ値（最大値）
    :param int vocal: 基礎ボーカルアピール値（最大値）
    :param int dance: 基礎ダンスアピール値（最大値）
    :param int visual: 基礎ビジュアルアピール値（最大値）
    :param int affection: 親愛度（最大値）
    :param str buff_class: センター効果
    :param str buff: センター効果説明
    :param str skill_class: 特技
    :param str skill: 特技説明
    """

    ruby: str = "ふりがな"  # ふりがな。アイドル情報（idols, profiles）のアクセスキー。
    episode: str = "エピソード"  # エピソード。エピソード情報（episodes, flavors, buffs, skills）へのアクセスキー。
    type: IdolType = field(default=IdolType.NA, compare=False)  # アイドルタイプ
    dominant: DominantType = field(default=DominantType.NA, compare=False)  # ドミナントアイドルタイプ
    mystyle: bool = field(default=False, compare=False)  # マイスタイル
    rare: RareClass = field(default=RareClass.N, compare=False)  # レア度
    star_rank: int = field(default=0, compare=False)  # スターランク
    skill_level: int = field(default=0, compare=False)  # 特技レベル
    level: int = field(default=1, compare=False)  # レベル
    affection: int = field(default=0, compare=False)  # 親愛度
    vocal: int = field(default=0, compare=False)  # ボーカル
    dance: int = field(default=0, compare=False)  # ダンス
    visual: int = field(default=0, compare=False)  # ビジュアル
    life: int = field(default=0, compare=False)  # ライフ
    buff_class: str = field(default="センター効果", compare=False)  # センター効果
    buff: str = field(default="センター効果説明", compare=False)  # センター効果説明
    skill_class: str = field(default="特技", compare=False)  # 特技
    skill: str = field(default="特技説明", compare=False)  # 特技説明


class Episodes:
    """
    エピソード（``Episode``）の基本情報データベース。
    """

    def __init__(self) -> None:
        self._episodes: set[Episode] = set()
        self._path: Path = Path(EPISODESDB)

    @property
    def filename(self) -> str:
        """
        エピソードの基本情報データベースのファイル名。
        """

        return self._path.name

    @filename.setter
    def filename(self, value: str) -> None:
        self._path = Path(value)

    def get(self, episode: str) -> Episode:
        """
        エピソード名を条件にデータベースからエピソードの基本情報を取り出す。

        :param str episode: 抽出条件のエピソード名。

        :return: エピソード名を条件に取り出されたエピソードの基本情報。
        :rtype: Episode
        """

        result: set[Episode] = {epi for epi in self._episodes if epi.episode == episode}
        return result.pop() if result else Episode()

    def gets(self) -> set[Episode]:
        """
        get
        """

        return self._episodes

    def add(self, idol: Episode) -> None:
        """
        エピソードの基本情報データベースにエピソードの基本情報を追加する。

        :param Episode idol: 追加するエピソードの基本情報。
        """

        self._episodes.add(idol)

    def remove(self, idol: Episode) -> None:
        """
        エピソードの基本情報データベースにエピソードの基本情報を削除する。

        :param Episode idol: 削除するエピソードの基本情報。
        """

        self._episodes.remove(idol)

    def update(self, after: Episode, before: Episode) -> None:
        """
        エピソードの基本情報の更新を行う。

        :param Episode after: 更新後のエピソードの基本情報。
        :param Episode before: 更新前のエピソードの基本情報。

        :raise EpisodesError: **before** がエピソードの基本情報データベースに存在しない。
        """
        if after.episode != before.episode:
            raise EpisodesError(f"{self.__class__.__name__}.updata: ")

        self.remove(before)
        self.add(after)

    def load(self) -> None:
        """
        エピソードの基本情報データベースを読み込む。
        """

        if not isinstance(self._path, Path) or not self._path.exists():
            raise EpisodesError(f"{self.__class__.__name__}.load: ")

        with self._path.open("r", encoding="utf-8-sig") as f:
            datas = json.load(f)

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
            self._episodes.add(episode)

        LibsEpisodesLogger.info(
            f"{self.__class__.__name__}.load: {len(self._episodes)}件のエピソード基本情報を読み込みました。"
        )

    def save(self) -> None:
        """
        エピソードの基本情報データベースを保存する。
        """

        if not isinstance(self._path, Path):
            raise EpisodesError(f"{self.__class__.__name__}.save: ")

        episodes = [
            {
                "ふりがな": episode.ruby,
                "エピソード": episode.episode,
                "アイドルタイプ": IdolType(episode.type),
                "ドミナントアイドルタイプ": DominantType(episode.dominant),
                "マイスタイル": str(episode.mystyle),
                "レア度": RareClass(episode.rare),
                "スターランク": int(episode.star_rank),
                "特技レベル": int(episode.skill_level),
                "レベル": int(episode.level),
                "親愛度": int(episode.affection),
                "ボーカル": int(episode.vocal),
                "ダンス": int(episode.dance),
                "ビジュアル": int(episode.visual),
                "ライフ": int(episode.life),
                "センター効果": episode.buff_class,
                "センター効果説明": episode.buff,
                "特技": episode.skill_class,
                "特技説明": episode.skill,
            }
            for episode in sorted(self.gets())
        ]

        with self._path.open("w", encoding="utf-8") as f:
            json.dump(episodes, f, indent=4, ensure_ascii=False)

        LibsEpisodesLogger.info(f"{self.__class__.__name__}.save: エピソード基本情報データベースを保存しました。")


if __name__ == "__main__":
    print(__file__)
