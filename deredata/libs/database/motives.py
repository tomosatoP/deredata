"""
ボーカル／ダンス／ビジュアルモチーフの効果量を扱うモジュール。

モチーフの効果量は対応するアピール値で決まるので、アピール値－効果量の変換表が必要。
"""

import json
from pathlib import Path
from dataclasses import dataclass

from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsMotifLogger

# 特技モチーフ効果量のデータベースのファイル名。
MOTIFDB: str = database_folder() + "motif.json"


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

    _motives: list[Motif] = list()
    _motives_grand: list[Motif] = list()

    def value(self, appeal: int, grand: bool = False) -> float:
        """
        特技モチーフの効果量。

        アピール値によって決まる特技モチーフの効果量。

        :param int appeal: アピール値。
        :param bool grand: ``True`` の場合にグランドライブ用の特技効果量、初期値 ``False`` の時はそれ以外の特技効果量。

        :retrun: 特技効果量。
        :rtype: float
        """

        database = self.__class__._motives if not grand else self.__class__._motives_grand

        return [motif.rate for motif in database if motif.appeal <= appeal][-1]

    def add_motif(self, motif: Motif) -> None:
        self.__class__._motives.append(motif)

    def add_motif_grand(self, motif: Motif) -> None:
        self.__class__._motives_grand.append(motif)

    @classmethod
    def _clear(cls) -> None:
        cls._motives.clear()
        cls._motives_grand.clear()

    @classmethod
    def load(cls, filename: str = MOTIFDB) -> None:
        """
        特技モチーフ効果量のデータを読み込む。
        """

        path = Path(filename)
        if any([not isinstance(path, Path), not path.exists(), not path.is_file()]):
            raise MotifError(f"{cls.__name__}.load: ")

        cls._clear()

        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
            for motif in data["通常ライブ"]:
                cls._motives.append(
                    Motif(
                        appeal=int(motif["アピール値"]),
                        rate=float(motif["倍率"]),
                    )
                )
            for motif in data["グランドライブ"]:
                cls._motives_grand.append(
                    Motif(
                        appeal=int(motif["アピール値"]),
                        rate=float(motif["倍率"]),
                    )
                )

        number: int = len(cls._motives) + len(cls._motives_grand)
        LibsMotifLogger.info(f"{cls.__name__}.load: {number}件の特技モチーフ効果量を読み込みました。")

    @classmethod
    def save(cls, filename: str = MOTIFDB) -> None:
        """
        特技モチーフ効果量のデータを保存。
        """

        path: Path = Path(filename)
        if not isinstance(path, Path):
            raise MotifError(f"{cls.__name__}.save: ")

        motifdb = [
            {
                "アピール値": motif.appeal,
                "倍率": motif.rate,
            }
            for motif in cls._motives
        ]

        motifdb_grand = [
            {
                "アピール値": motif.appeal,
                "倍率": motif.rate,
            }
            for motif in cls._motives_grand
        ]

        with path.open("w", encoding="utf-8") as f:
            json.dump({"通常ライブ": motifdb, "グランドライブ": motifdb_grand}, f, indent=4, ensure_ascii=False)

        number: int = len(cls._motives) + len(cls._motives_grand)
        LibsMotifLogger.info(f"{cls.__name__}.save: {number}件の特技モチーフ効果量データベースを保存しました。")


if __name__ == "__main__":
    print(__file__)
