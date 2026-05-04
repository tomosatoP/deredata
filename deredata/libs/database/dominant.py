"""
特技ドミナント・ハーモニーの効果量を扱うモジュール。

効果量は対応するアイドルの編成人数で決まるので、アイドルの編成人数－効果量の変換表が必要。

:class Dominant: 特技ドミナント・ハーモニーの基礎情報のデータクラス。
:class Dominants: 特技ドミナント・ハーモニーの効果量のデータベースクラス。
"""

import json
from pathlib import Path
from dataclasses import dataclass

from kivy.logger import Logger as LibsDominantLogger

DOMINANTDB = "database/dominant.json"


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

    def __init__(self) -> None:
        self._dominants_guest: list[Dominant] = list()
        self._dominants_noguest: list[Dominant] = list()
        self._path = Path(DOMINANTDB)

    @property
    def filename(self) -> str:
        """
        特技ドミナント・ハーモニー効果量データベースのファイル名。
        """

        return self._path.name

    @filename.setter
    def filename(self, value: str) -> None:
        self._path = Path(value)

    def value(self, number: int, type: int, guest: bool = True) -> float:
        """
        特技ドミナント・ハーモニーの効果量。

        アイドルの編成人数によって決まる特技モチーフの効果量。

        :param int number: アイドルの編成人数。
        :param int type: ``0`` の時は、スコアボーナス効果量。``1`` の時は、COMBOボーナス効果量。
        :param bool guest: 初期値 ``True`` の場合にゲスト有り。``False`` の時はゲスト無し。

        :retrun: 特技効果量。
        :rtype: float
        """

        database = self._dominants_guest if guest else self._dominants_noguest
        result = list(filter(lambda d: d.number == number, database))[0]

        return result.score if type == 0 else result.combo

    def load(self, path: Path | None = None) -> None:
        """
        特技ドミナント・ハーモニーの効果量のデータベースを読み込む。
        """

        self._dominants_guest.clear()
        self._dominants_noguest.clear()

        if not isinstance(self._path, Path) or not self._path.exists():
            raise DominantError(f"{self.__class__.__name__}.load: ")

        with self._path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
            for dominant in data["ゲスト有り"]:
                self._dominants_guest.append(
                    Dominant(
                        number=int(dominant["編成人数"]),
                        score=float(dominant["スコアボーナス"]),
                        combo=float(dominant["COMBOボーナス"]),
                    )
                )
            for dominant in data["ゲスト無し"]:
                self._dominants_noguest.append(
                    Dominant(
                        number=int(dominant["編成人数"]),
                        score=float(dominant["スコアボーナス"]),
                        combo=float(dominant["COMBOボーナス"]),
                    )
                )

        LibsDominantLogger.info(
            f"{self.__class__.__name__}.load: {
                len(self._dominants_guest) + len(self._dominants_noguest)
            }件の特技ドミナント・ハーモニー効果量を読み込みました。"
        )

    def save(self) -> None:
        """
        特技ドミナント・ハーモニーの効果量のデータベースを保存する。
        """

        if not isinstance(self._path, Path):
            raise DominantError(f"{self.__class__.__name__}.save: ")

        guestdb = [
            {
                "編成人数": dominant.number,
                "スコアボーナス": dominant.score,
                "COMBOボーナス": dominant.combo,
            }
            for dominant in self._dominants_guest
        ]

        noguestdb = [
            {
                "編成人数": dominant.number,
                "スコアボーナス": dominant.score,
                "COMBOボーナス": dominant.combo,
            }
            for dominant in self._dominants_noguest
        ]

        with self._path.open("w", encoding="utf-8") as f:
            json.dump({"ゲスト有り": guestdb, "ゲスト無し": noguestdb}, f, indent=4, ensure_ascii=False)

        LibsDominantLogger.info(
            f"{self.__class__.__name__}.save: 特技ドミナント・ハーモニー効果量データベースを保存しました。"
        )


if __name__ == "__main__":
    print(__file__)
