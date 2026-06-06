"""
エピソードのフレーバを扱うモジュール。

:dataclass Flavor: エピソードのフレーバのデータクラス。
:class Flavors: エピソードのフレーバのデータベース。
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from setuptools._distutils.util import strtobool

from deredata.libs.database.enumerations import GachaType
from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsFlavorsLogger

# アイドルのフレーバーのデータベースファイル名
FLAVORSDB: str = database_folder() + "flavors.json"


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
    gacha: GachaType = field(default=GachaType.NORMAL, compare=False)  # 入手枠
    registration_date: str = field(default="登録日", compare=False)  # 登録日


class Flavors:
    """
    エピソードのフレーバのデータベース。
    """

    _flavors: set[Flavor] = set()

    def get(self, episode: str) -> Flavor:
        """
        エピソード名を条件にデータベースアからエピソードのフレーバーを取り出す。

        :param str episode: 抽出条件のエピソード名。

        :return: エピソード名を条件に取り出したエピソードのフレーバー。
        :rtype: Falvor
        """

        return {flavor for flavor in Flavors._flavors if flavor.episode == episode}.pop()

    def gets(self) -> set[Flavor]:
        """
        データベースから全エピソードのフレーバの集合を取り出す。

        :return: 全エピソードのフレーバーの集合。
        :rtype: set[Flavor]
        """

        return Flavors._flavors

    def add(self, flavor: Flavor) -> None:
        """
        エピソードのフレーバをエピソードのフレーバのデータベースに追加する。

        :param Flavor flavor: 追加するエピソードのフレーバー
        """

        Flavors._flavors.add(flavor)

    def remove(self, flavor: Flavor) -> None:
        """
        エピソードのフレーバをエピソードのフレーバのデータベースから削除する。

        :param Flavor flavor: 削除するエピソードのフレーバー。
        """

        Flavors._flavors.remove(flavor)

    @classmethod
    def load(cls, filename: str = FLAVORSDB) -> None:
        """
        エピソードのフレーバのデータベースを読み込む。
        """

        path = Path(filename)
        if any([not isinstance(path, Path), not path.exists(), not path.is_file()]):
            raise FlavorsError(f"{cls.__name__}.load: ")

        with path.open(encoding="utf-8") as f:
            datas = json.load(f)

        for data in datas:
            flavor = Flavor(
                episode=data["エピソード"],
                voice=strtobool(data["ボイス"]),
                solo=strtobool(data["ソロ"]),
                gacha=GachaType(data["入手枠"]),
                registration_date=data["登録日"],
            )
            Flavors._flavors.add(flavor)

        LibsFlavorsLogger.info(
            f"{cls.__name__}.load: {len(cls._flavors)}件のエピソードフレーバー情報データベースを読み込みました。"
        )

    @classmethod
    def save(cls, filename: str = FLAVORSDB) -> None:
        """
        エピソードのフレーバのデータベースを保存する。
        """

        path: Path = Path(filename)
        if not isinstance(path, Path):
            raise FlavorsError(f"{cls.__name__}.save: ")

        datas = [
            {
                "エピソード": flavor.episode,
                "ボイス": str(flavor.voice),
                "ソロ": str(flavor.solo),
                "入手枠": GachaType(flavor.gacha),
                "登録日": flavor.registration_date,
            }
            for flavor in sorted(cls._flavors)
        ]

        with path.open("w", encoding="utf-8") as f:
            json.dump(datas, f, ensure_ascii=False, indent=4)

        LibsFlavorsLogger.info(
            f"{cls.__name__}.save:  {len(cls._flavors)}件のエピソードフレーバー情報データベースを保存しました。"
        )


if __name__ == "__main__":
    print(__file__)
