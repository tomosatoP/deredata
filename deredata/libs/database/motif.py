"""
ボーカル／ダンス／ビジュアルモチーフの効果量を扱うモジュール。

モチーフの効果量は対応するアピール値で決まるので、アピール値－効果量の変換表が必要。
"""

import json
from pathlib import Path
from dataclasses import dataclass

from kivy.logger import Logger as LibsMotifLogger

MOTIFDB = "database/motif.json"


class MotifError(Exception):
    """
    motifのエラーハンドラ
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsMotifLogger.error(f"MotifError: {args}")


@dataclass
class Motif:
    """
    モチーフの基礎情報。

    :param int appeal: アピール値（下限）。
    :param float rate: 特技（スコアボーナス）効果量。
    """

    appeal: int = 0
    rate: float = 0.0


class Motives:
    """
    特技モチーフ効果量のデータベースクラス。
    """

    def __init__(self) -> None:
        self._motives: list[Motif] = list()
        self._motives_grand: list[Motif] = list()
        self._path = Path(MOTIFDB)

    @property
    def filename(self) -> str:
        """特技モチーフ効果量データベースのファイル名。"""
        return self._path.name

    @filename.setter
    def filename(self, value: str) -> None:
        self._path = Path(value)

    def value(self, appeal: int, grand: bool = False) -> float:
        """
        特技モチーフの効果量。

        アピール値によって決まる特技モチーフの効果量。

        :param int appeal: アピール値。
        :param bool grand: ``True`` の場合にグランドライブ用の特技効果量、初期値 ``False`` の時はそれ以外の特技効果量。

        :retrun: 特技効果量。
        :rtype: float
        """

        database = self._motives if not grand else self._motives_grand

        return [motif.rate for motif in database if motif.appeal <= appeal][-1]

    def load(self, path: Path | None = None) -> None:
        """
        特技モチーフ効果量のデータを読み込む。
        """
        self._motives.clear()
        self._motives_grand.clear()

        if not isinstance(self._path, Path) or not self._path.exists():
            raise MotifError(f"{self.__class__.__name__}.load: ")

        with self._path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
            for motif in data["通常ライブ"]:
                self._motives.append(
                    Motif(
                        appeal=int(motif["アピール値"]),
                        rate=float(motif["倍率"]),
                    )
                )
            for motif in data["グランドライブ"]:
                self._motives_grand.append(
                    Motif(
                        appeal=int(motif["アピール値"]),
                        rate=float(motif["倍率"]),
                    )
                )

        LibsMotifLogger.info(
            f"{self.__class__.__name__}.load: {
                (len(self._motives) + len(self._motives_grand))
            }件の特技モチーフ効果量を読み込みました。"
        )

    def save(self) -> None:
        """
        特技モチーフ効果量のデータを保存。
        """

        if not isinstance(self._path, Path):
            raise MotifError(f"{self.__class__.__name__}.save: ")

        motifdb = [
            {
                "アピール値": motif.appeal,
                "倍率": motif.rate,
            }
            for motif in self._motives
        ]

        motifdb_grand = [
            {
                "アピール値": motif.appeal,
                "倍率": motif.rate,
            }
            for motif in self._motives_grand
        ]

        with self._path.open("w", encoding="utf-8") as f:
            json.dump({"通常ライブ": motifdb, "グランドライブ": motifdb_grand}, f, indent=4, ensure_ascii=False)

        LibsMotifLogger.info(f"{self.__class__.__name__}.save: 特技モチーフ効果量データベースを保存しました。")


if __name__ == "__main__":
    print(__file__)
