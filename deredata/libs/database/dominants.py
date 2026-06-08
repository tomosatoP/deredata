"""
特技ドミナント・ハーモニーの効果量を扱うモジュール。

効果量は対応するアイドルの編成人数で決まるので、アイドルの編成人数－効果量の変換表が必要。

:class Dominant: 特技ドミナント・ハーモニーの基礎情報のデータクラス。
:class Dominants: 特技ドミナント・ハーモニーの効果量のデータベースクラス。
"""

import json
from pathlib import Path
from dataclasses import dataclass

from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsDominantLogger

# 特技ドミナント・ハーモニーの効果量のデータベースのファイル名。
DOMINANTDB: str = database_folder() + "dominant.json"


class DominantError(Exception):
    """
    dominantのエラーハンドラ
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsDominantLogger.error(f"DominantError: {args}")


@dataclass
class Dominant:
    """
    特技ドミナント・ハーモニーの基礎情報のデータクラス。

    :param int number: アイドルの編成人数。
    :param float score: 特技スコアボーナス効果量。
    :param float combo: 特技COMBOボーナス効果量。
    """

    number: int = 0
    score: float = 0.0
    combo: float = 0.0


class Dominants:
    """
    特技ドミナント・ハーモニーの効果量のデータベースクラス。
    """

    _dominants_with_guest: list[Dominant] = list()
    _dominants_without_guest: list[Dominant] = list()

    def value(self, number: int, type: int, guest: bool = True) -> float:
        """
        特技ドミナント・ハーモニーの効果量。

        アイドルの編成人数によって決まる特技モチーフの効果量。

        :param int number: アイドルの編成人数。
        :param int type: ``0`` の時は、スコアブースト効果量。``1`` の時は、COMBOブースト効果量。
        :param bool guest: 初期値 ``True`` の場合にゲスト有り。``False`` の時はゲスト無し。

        :retrun: 特技効果量。
        :rtype: float
        """

        database = self.__class__._dominants_with_guest if guest else self.__class__._dominants_without_guest
        result = list(filter(lambda d: d.number == number, database))[0]

        return result.score if type == 0 else result.combo

    def add_with_guest(self, dominant: Dominant) -> None:
        self.__class__._dominants_with_guest.append(dominant)

    def add_without_guest(self, dominant: Dominant) -> None:
        self.__class__._dominants_without_guest.append(dominant)

    @classmethod
    def _clear(cls) -> None:
        cls._dominants_with_guest.clear()
        cls._dominants_without_guest.clear()

    @classmethod
    def load(cls, filename: str = DOMINANTDB) -> None:
        """
        特技ドミナント・ハーモニーの効果量のデータベースを読み込む。
        """

        path = Path(filename)
        if any([not isinstance(path, Path), not path.exists(), not path.is_file()]):
            raise DominantError(f"{cls.__name__}.load: ")

        cls._clear()
        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
            for dominant in data["ゲスト有り"]:
                cls._dominants_with_guest.append(
                    Dominant(
                        number=int(dominant["編成人数"]),
                        score=float(dominant["スコアボーナス"]),
                        combo=float(dominant["COMBOボーナス"]),
                    )
                )
            for dominant in data["ゲスト無し"]:
                cls._dominants_without_guest.append(
                    Dominant(
                        number=int(dominant["編成人数"]),
                        score=float(dominant["スコアボーナス"]),
                        combo=float(dominant["COMBOボーナス"]),
                    )
                )

        number: int = len(cls._dominants_with_guest) + len(cls._dominants_without_guest)
        LibsDominantLogger.info(f"{cls.__name__}.load: {number}件の特技ドミナント・ハーモニー効果量を読み込みました。")

    @classmethod
    def save(cls, filename: str = DOMINANTDB) -> None:
        """
        特技ドミナント・ハーモニーの効果量のデータベースを保存する。
        """

        path: Path = Path(filename)
        if not isinstance(path, Path):
            raise DominantError(f"{cls.__name__}.save: ")

        guestdb = [
            {
                "編成人数": dominant.number,
                "スコアボーナス": dominant.score,
                "COMBOボーナス": dominant.combo,
            }
            for dominant in cls._dominants_with_guest
        ]

        noguestdb = [
            {
                "編成人数": dominant.number,
                "スコアボーナス": dominant.score,
                "COMBOボーナス": dominant.combo,
            }
            for dominant in cls._dominants_without_guest
        ]

        with path.open("w", encoding="utf-8") as f:
            json.dump({"ゲスト有り": guestdb, "ゲスト無し": noguestdb}, f, indent=4, ensure_ascii=False)

        number: int = len(cls._dominants_with_guest) + len(cls._dominants_without_guest)
        LibsDominantLogger.info(
            f"{cls.__name__}.save: {number}件の特技ドミナント・ハーモニー効果量データベースを保存しました。"
        )


if __name__ == "__main__":
    print(__file__)
