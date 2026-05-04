"""
特技ライフスパークルの効果量を扱うモジュール。

効果量（倍率）は対応する残ライフ値で決まるので、残ライフ値－効果量（倍率）の変換表が必要。
"""

import json
from pathlib import Path
from dataclasses import dataclass

from kivy.logger import Logger as LibsLifesparkleLogger

LIFESPARKLEDB = "database/lifesparkle.json"


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

    def __init__(self) -> None:
        self._lifesparkles_ssr: list[Lifesparkle] = list()
        self._lifesparkles_sr: list[Lifesparkle] = list()
        self._path = Path(LIFESPARKLEDB)

    @property
    def filename(self) -> str:
        """特技ライフスパークル効果量データベースのファイル名。"""
        return self._path.name

    @filename.setter
    def filename(self, value: str) -> None:
        self._path = Path(value)

    def value(self, life: int, rare: str = "SSR") -> float:
        """
        特技ライフスパークルの効果量。

        残ライフ値によって決まる特技ライフスパークルの効果量。

        :param int life: 残ライフ値。
        :param str rare: 初期値 ``SSR`` の場合にレア度SSR/SSR+。``SR`` の時はレア度SR/SR+。

        :retrun: 特技効果量。
        :rtype: float
        """

        database = self._lifesparkles_ssr if rare == "SSR" else self._lifesparkles_sr

        return list(filter(lambda d: d.life <= life, database))[-1].rate

    def load(self, path: Path | None = None) -> None:
        """
        特技ライフスパークルの効果量（倍率）のデータを読み込む。
        """
        self._lifesparkles_ssr.clear()
        self._lifesparkles_sr.clear()

        if not isinstance(self._path, Path) or not self._path.exists():
            raise LifesparkleError(f"{self.__class__.__name__}.load: ")

        with self._path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
            for lifesparkle in data["ＳＳＲ"]:
                self._lifesparkles_ssr.append(
                    Lifesparkle(
                        life=int(lifesparkle["残ライフ値"]),
                        rate=float(lifesparkle["倍率"]),
                    )
                )
            for lifesparkle in data["ＳＲ"]:
                self._lifesparkles_sr.append(
                    Lifesparkle(
                        life=int(lifesparkle["残ライフ値"]),
                        rate=float(lifesparkle["倍率"]),
                    )
                )
        LibsLifesparkleLogger.info(
            f"{self.__class__.__name__}.load. {
                (len(self._lifesparkles_ssr) + len(self._lifesparkles_sr))
            }件の特技ライフスパークル効果量を読み込みました。"
        )

    def save(self) -> None:
        """
        特技ライフスパークルの効果量のデータを保存。
        """

        if not isinstance(self._path, Path):
            raise LifesparkleError(f"{self.__class__.__name__}.save: ")

        ssrdb = [
            {
                "残ライフ値": lifesparkle.life,
                "倍率": lifesparkle.rate,
            }
            for lifesparkle in self._lifesparkles_ssr
        ]

        srdb = [
            {
                "残ライフ値": lifesparkle.life,
                "倍率": lifesparkle.rate,
            }
            for lifesparkle in self._lifesparkles_sr
        ]

        with self._path.open("w", encoding="utf-8") as f:
            json.dump({"ＳＳＲ": ssrdb, "ＳＲ": srdb}, f, indent=4, ensure_ascii=False)

        LibsLifesparkleLogger.info(
            f"{self.__class__.__name__}.save. 特技ライフスパークル効果量データベースを保存しました。"
        )


if __name__ == "__main__":
    print(__file__)
