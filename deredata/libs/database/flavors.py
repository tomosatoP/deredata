"""
エピソードのフレーバを扱うモジュール。

:dataclass Flavor: エピソードのフレーバのデータクラス。
:class Flavors: エピソードのフレーバのデータベース。
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from setuptools._distutils.util import strtobool

from deredata.libs.database import enums

from kivy.logger import Logger as LibsFlavorsLogger

FLAVORSDB = "database/flavors.json"


class FlavorsError(Exception):
    """flavorsのエラーハンドラ"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsFlavorsLogger.error(f"FlavorsError: {args}")


@dataclass(order=True, frozen=True)
class Flavor:
    """
    エピソードのフレーバのデータクラス。

    :param str episode: エピソード名（アクセスキー）
    :param bool voice: ボイスの有無
    :param bool solo: ソロVerの有無
    :param enums.GachaType gacha: 入手枠
    :param str registration_date: 登録日
    """

    episode: str = "エピソード"  # エピソード。エピソード情報（episodes, flavors, buffs, skills）へのアクセスキー。
    voice: bool = field(default=False, compare=False)  # ボイス
    solo: bool = field(default=False, compare=False)  # ソロ
    gacha: enums.GachaType = field(default=enums.GachaType.NORMAL, compare=False)  # 入手枠
    registration_date: str = field(default="登録日", compare=False)  # 登録日


class Flavors:
    """
    エピソードのフレーバのデータベース。
    """

    def __init__(self) -> None:
        self._flavors: set[Flavor] = set()
        self._path: Path = Path(FLAVORSDB)

    @property
    def filename(self) -> str:
        """
        エピソードのフレーバのデータベースのファイル名。
        """

        return self._path.name

    @filename.setter
    def filename(self, value: str) -> None:
        self._path = Path(value)

    def get(self, episode: str) -> Flavor:
        """
        エピソード名を条件にデータベースアからエピソードのフレーバーを取り出す。

        :param str episode: 抽出条件のエピソード名。

        :return: エピソード名を条件に取り出したエピソードのフレーバー。
        :rtype: Falvor
        """

        return {flavor for flavor in self._flavors if flavor.episode == episode}.pop()

    def gets(self) -> set[Flavor]:
        """
        データベースから全エピソードのフレーバの集合を取り出す。

        :return: 全エピソードのフレーバーの集合。
        :rtype: set[Flavor]
        """

        return self._flavors

    def add(self, flavor: Flavor) -> None:
        """
        エピソードのフレーバをエピソードのフレーバのデータベースに追加する。

        :param Flavor flavor: 追加するエピソードのフレーバー
        """

        self._flavors.add(flavor)

    def remove(self, flavor: Flavor) -> None:
        """
        エピソードのフレーバをエピソードのフレーバのデータベースから削除する。

        :param Flavor flavor: 削除するエピソードのフレーバー。
        """

        self._flavors.remove(flavor)

    def load(self) -> None:
        """
        エピソードのフレーバのデータベースを読み込む。
        """

        if not isinstance(self._path, Path) or not self._path.exists():
            raise FlavorsError(f"{self.__class__.__name__}.load: ")

        with self._path.open(encoding="utf-8") as f:
            datas = json.load(f)

        for data in datas:
            flavor = Flavor(
                episode=data["エピソード"],
                voice=strtobool(data["ボイス"]),
                solo=strtobool(data["ソロ"]),
                gacha=enums.GachaType(data["入手枠"]),
                registration_date=data["登録日"],
            )
            self._flavors.add(flavor)

        LibsFlavorsLogger.info(
            f"{self.__class__.__name__}.load:  {len(self._flavors)}件のエピソードフレーバー情報を読み込みました。"
        )

    def save(self) -> None:
        """
        エピソードのフレーバのデータベースを保存する。
        """

        if not isinstance(self._path, Path):
            raise FlavorsError(f"{self.__class__.__name__}.save: ")

        datas = [
            {
                "エピソード": flavor.episode,
                "ボイス": str(flavor.voice),
                "ソロ": str(flavor.solo),
                "入手枠": enums.GachaType(flavor.gacha),
                "登録日": flavor.registration_date,
            }
            for flavor in sorted(self.gets())
        ]

        with self._path.open("w", encoding="utf-8") as f:
            json.dump(datas, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    print(__file__)
