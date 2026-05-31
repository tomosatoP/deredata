"""
スコア計算で使うコンボ倍率のモジュール。

コンボ倍率は、総ノート数に対するコンボ数の割合によって決まる倍率のこと。

:dataclass Comborate: コンボ倍率のデータクラス。
:class ComboRates: コンボ倍率データベース。
"""

import json
from pathlib import Path
from dataclasses import dataclass

from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsComboratesLogger

COMBORATESDB: str = database_folder() + "comborates.json"


class ComboratesError(Exception):
    """Comboratesのエラーハンドラ。"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsComboratesLogger.error(f"ComboratesError: {args}")


@dataclass
class Comborate:
    """
    コンボ倍率のデータクラス。

    :param float ulimit: 上限：総ノートする対するコンボ数の割合。
    :param float rate: コンボ倍率。
    """

    ulimit: float = 0.0  # 上限：総ノートする対するコンボ数の割合
    rate: float = 0.0  # コンボ倍率


class ComboRates:
    """
    コンボ倍率データベース。
    """

    def __init__(self) -> None:
        self._rates: list[Comborate] = list()
        self._path: Path = Path(COMBORATESDB)

    @property
    def filename(self) -> str:
        """
        コンボ倍率データベースのファイル名。
        """

        return self._path.name

    @filename.setter
    def filename(self, value: str) -> None:
        self._path = Path(value)

    def rate(self, ratio: float) -> float:
        """
        コンボ倍率。

        コンボ倍率は、総ノート数に対するコンボ数の割合によって決まる倍率。

        :param float ration: 総ノート数に対するコンボ数の割合。

        :return: コンボ倍率。
        :rtype: float
        """

        return [comborate.rate for comborate in self._rates if comborate.ulimit >= ratio][0]

    def add(self, comborate: Comborate) -> None:
        """
        コンボ倍率をコンボ倍率データベースに追加する。

        :param Comborate comborate: 追加するコンボ倍率。
        """

        self._rates.append(comborate)

    def load(self) -> None:
        """
        コンボ倍率データベースを読み込む。
        """

        self._rates.clear()

        if not isinstance(self._path, Path) or not self._path.exists():
            raise ComboratesError(f"{self.__class__.__name__}.load: ")

        with self._path.open("r", encoding="utf-8-sig") as f:
            datas = json.load(f)

            for data in datas:
                self._rates.append(
                    Comborate(
                        ulimit=float(data["上限"]),
                        rate=float(data["コンボ倍率"]),
                    )
                )
        LibsComboratesLogger.info(f"{self.__class__.__name__}.load: {len(self._rates)}件のコンボ倍率を読み込みました。")

    def save(self) -> None:
        """
        コンボ倍率データベースを保存する。
        """

        if not isinstance(self._path, Path):
            raise ComboratesError(f"{self.__class__.__name__}.save: ")

        comborates = [
            {
                "上限": comborate.ulimit,
                "コンボ倍率": comborate.rate,
            }
            for comborate in self._rates
        ]

        with self._path.open("w", encoding="utf-8") as f:
            json.dump(comborates, f, indent=4, ensure_ascii=False)

        LibsComboratesLogger.info(f"{self.__class__.__name__}.save: コンボ倍率データベースを保存しました。")


if __name__ == "__main__":
    print(__file__)
