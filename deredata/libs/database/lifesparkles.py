"""
特技ライフスパークルの効果量を扱うモジュール。

効果量（倍率）は対応する残ライフ値で決まるので、残ライフ値－効果量（倍率）の変換表が必要。
"""

import json
from pathlib import Path
from dataclasses import dataclass

from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsLifesparkleLogger

# 特技ライフスパークルの効果量のデータベースのファイル名。
LIFESPARKLEDB: str = database_folder() + "lifesparkle.json"


class LifesparkleError(Exception):
    """
    lifesparkleのエラーハンドラ
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsLifesparkleLogger.error(f"LifesparkleError: {args}")


@dataclass
class Lifesparkle:
    """
    特技ライフスパークルの効果量の基礎情報。

    :param int life: 残ライフ値。
    :param float rate: 効果量（倍率）。
    """

    life: int = 0
    rate: float = 0.0


class Lifesparkles:
    """
    特技ライフスパークルの効果量のデータベースクラス。
    """

    _lifesparkles_ssr: list[Lifesparkle] = list()
    _lifesparkles_sr: list[Lifesparkle] = list()

    def value(self, life: int, rare: str = "SSR") -> float:
        """
        特技ライフスパークルの効果量。

        残ライフ値によって決まる特技ライフスパークルの効果量。

        :param int life: 残ライフ値。
        :param str rare: 初期値 ``SSR`` の場合にレア度SSR/SSR+。``SR`` の時はレア度SR/SR+。

        :retrun: 特技効果量。
        :rtype: float
        """

        database = self.__class__._lifesparkles_ssr if rare == "SSR" else self.__class__._lifesparkles_sr

        return list(filter(lambda d: d.life <= life, database))[-1].rate

    def add_ssr(self, lifesparkle: Lifesparkle) -> None:
        self.__class__._lifesparkles_ssr.append(lifesparkle)

    def add_sr(self, lifesparkle: Lifesparkle) -> None:
        self.__class__._lifesparkles_sr.append(lifesparkle)

    @classmethod
    def _clear(cls) -> None:
        cls._lifesparkles_ssr.clear()
        cls._lifesparkles_sr.clear()

    @classmethod
    def load(cls, filename: str = LIFESPARKLEDB) -> None:
        """
        特技ライフスパークルの効果量（倍率）のデータを読み込む。
        """

        path = Path(filename)
        if any([not isinstance(path, Path), not path.exists(), not path.is_file()]):
            raise LifesparkleError(f"{cls.__name__}.load: ")

        cls._clear()
        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
            for lifesparkle in data["ＳＳＲ"]:
                cls._lifesparkles_ssr.append(
                    Lifesparkle(
                        life=int(lifesparkle["残ライフ値"]),
                        rate=float(lifesparkle["倍率"]),
                    )
                )
            for lifesparkle in data["ＳＲ"]:
                cls._lifesparkles_sr.append(
                    Lifesparkle(
                        life=int(lifesparkle["残ライフ値"]),
                        rate=float(lifesparkle["倍率"]),
                    )
                )

        number: int = len(cls._lifesparkles_ssr) + len(cls._lifesparkles_sr)
        LibsLifesparkleLogger.info(f"{cls.__name__}.load. {number}件の特技ライフスパークル効果量を読み込みました。")

    @classmethod
    def save(cls, filename: str = LIFESPARKLEDB) -> None:
        """
        特技ライフスパークルの効果量のデータを保存。
        """

        path: Path = Path(filename)
        if not isinstance(path, Path):
            raise LifesparkleError(f"{cls.__name__}.save: ")

        ssrdb = [
            {
                "残ライフ値": lifesparkle.life,
                "倍率": lifesparkle.rate,
            }
            for lifesparkle in cls._lifesparkles_ssr
        ]

        srdb = [
            {
                "残ライフ値": lifesparkle.life,
                "倍率": lifesparkle.rate,
            }
            for lifesparkle in cls._lifesparkles_sr
        ]

        with path.open("w", encoding="utf-8") as f:
            json.dump({"ＳＳＲ": ssrdb, "ＳＲ": srdb}, f, indent=4, ensure_ascii=False)

        number: int = len(cls._lifesparkles_ssr) + len(cls._lifesparkles_sr)
        LibsLifesparkleLogger.info(
            f"{cls.__name__}.save. {number}件の特技ライフスパークル効果量データベースを保存しました。"
        )


if __name__ == "__main__":
    print(__file__)
