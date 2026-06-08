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

# コンボ倍率データベースのファイル名。
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

    _rates: list[Comborate] = list()

    def rate(self, ratio: float) -> float:
        """
        コンボ倍率。

        コンボ倍率は、総ノート数に対するコンボ数の割合によって決まる倍率。

        :param float ration: 総ノート数に対するコンボ数の割合。

        :return: コンボ倍率。
        :rtype: float
        """

        return [comborate.rate for comborate in self.__class__._rates if comborate.ulimit >= ratio][0]

    def add(self, comborate: Comborate) -> None:
        """
        コンボ倍率をコンボ倍率データベースに追加する。

        :param Comborate comborate: 追加するコンボ倍率。
        """

        self.__class__._rates.append(comborate)

    @classmethod
    def _clear(cls) -> None:
        cls._rates.clear()

    @classmethod
    def load(cls, filename: str = COMBORATESDB) -> None:
        """
        コンボ倍率データベースを読み込む。
        """

        path = Path(filename)
        if any([not isinstance(path, Path), not path.exists(), not path.is_file()]):
            raise ComboratesError(f"{cls.__name__}.load: ")

        cls._clear()
        with path.open("r", encoding="utf-8-sig") as f:
            datas = json.load(f)

            for data in datas:
                cls._rates.append(
                    Comborate(
                        ulimit=float(data["上限"]),
                        rate=float(data["コンボ倍率"]),
                    )
                )

        LibsComboratesLogger.info(f"{cls.__name__}.load: {len(cls._rates)}件のコンボ倍率を読み込みました。")

    @classmethod
    def save(cls, filename: str = COMBORATESDB) -> None:
        """
        コンボ倍率データベースを保存する。
        """

        path: Path = Path(filename)
        if not isinstance(path, Path):
            raise ComboratesError(f"{cls.__name__}.save: ")

        comborates = [
            {
                "上限": comborate.ulimit,
                "コンボ倍率": comborate.rate,
            }
            for comborate in cls._rates
        ]

        with path.open("w", encoding="utf-8") as f:
            json.dump(comborates, f, indent=4, ensure_ascii=False)

        LibsComboratesLogger.info(f"{cls.__name__}.save: {len(cls._rates)}件のコンボ倍率データベースを保存しました。")


if __name__ == "__main__":
    print(__file__)
