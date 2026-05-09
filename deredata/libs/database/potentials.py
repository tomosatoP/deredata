"""
レア度別のポテンシャル補正値を扱うモジュール。

対象は、"ボーカル", "ダンス", "ビジュアル", "特技発動率", "ライフ"。

:dataclass Appeal: アピール値（"ボーカル", "ダンス", "ビジュアル"）のポテンシャル情報。
:dataclass Life: アピール値（"ライフ"）ポテンシャル情報。
:dataclass Ability: アピール値（"特技発動率"）のポテンシャル情報。
:class Potentials: ポテンシャルの基礎情報データベース。
"""

import json
from pathlib import Path
from dataclasses import dataclass

from deredata.libs.database.enumerations import RareClass
from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsPotentialsLogger

POTENTIALSDB: str = database_folder() + "potentials.json"


class PotentialsError(Exception):
    """
    ポテンシャルのエラーハンドラ
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsPotentialsLogger.error(f"PotentialsError: {args}")


@dataclass
class Appeal:
    """
    レア度別アピール（ボーカル、ダンス、ビジュアル）ポテンシャル。

    :param enums.RareClass rare: レア度。
    :param int level: レベル。
    :param int potential: ポテンシャル補正値。
    """

    rare: RareClass = RareClass.N
    level: int = 0
    potential: int = 0


@dataclass
class Life:
    """
    レア度別ライフポテンシャル。

    :param enums.RareClass rare: レア度。
    :param int level: レベル。
    :param int potential: ポテンシャル補正値。
    """

    rare: RareClass = RareClass.N
    level: int = 0
    potential: int = 0


@dataclass
class Ability:
    """
    レア度別アビリティ（特技発動率）ポテンシャル。

    :param enums.RareClass rare: レア度。
    :param int level: レベル。
    :param float potential: ポテンシャル補正値。
    """

    rare: RareClass = RareClass.N
    level: int = 0
    potential: float = 0.0


class Potentials:
    """
    ポテンシャルの基礎情報データベース。
    """

    def __init__(self) -> None:
        self._appeals: list[Appeal] = []
        self._abilities: list[Ability] = []
        self._lives: list[Life] = []
        self._path = Path(POTENTIALSDB)

    @property
    def filename(self) -> str:
        """
        ポテンシャルデータベースのファイル名。
        """

        return self._path.name

    @filename.setter
    def filename(self, value: str) -> None:
        self._path = Path(value)

    def value(self, type: str, rare: RareClass, level: int) -> float | int:
        """
        ポテンシャル補正値を取得する。

        :param str type: ポテンシャルタイプ ("ボーカル", "ダンス", "ビジュアル", "特技発動率", "ライフ")
        :param enums.RareClass rare: レア度
        :param int level: ポテンシャルレベル

        :return: ポテンシャル補正値。
        :type: float | int
        """

        match type:
            case "ボーカル" | "ダンス" | "ビジュアル":
                return list(filter(lambda appeal: appeal.rare == rare, self._appeals))[level].potential
            case "特技発動率":
                return list(filter(lambda ability: ability.rare == rare, self._abilities))[level].potential
            case "ライフ":
                return list(filter(lambda life: life.rare == rare, self._lives))[level].potential
            case _:
                raise PotentialsError(f"{self.__class__.__name__}.value: Invalid type '{type}'")

    def load(self) -> None:
        """
        ポテンシャルの基本情報データベースを読み込む。
        """

        self._appeals.clear()
        self._abilities.clear()
        self._lives.clear()

        if not isinstance(self._path, Path) or not self._path.exists():
            raise PotentialsError(f"{self.__class__.__name__}.load: ")

        with self._path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)

            for appeal in data["アピール値"]:
                self._appeals.append(
                    Appeal(
                        rare=RareClass(appeal["rare"]),
                        level=appeal["level"],
                        potential=appeal["potential"],
                    )
                )
            for ability in data["特技発動率"]:
                self._abilities.append(
                    Ability(
                        rare=RareClass(ability["rare"]),
                        level=ability["level"],
                        potential=ability["potential"],
                    )
                )
            for life in data["ライフ"]:
                self._lives.append(
                    Life(
                        rare=RareClass(life["rare"]),
                        level=life["level"],
                        potential=life["potential"],
                    )
                )

        LibsPotentialsLogger.info(
            f"{self.__class__.__name__}.load: {
                (len(self._appeals) + len(self._abilities) + len(self._lives))
            }件のポテンシャルデータを読み込みました。"
        )

    def save(self) -> None:
        """
        ポテンシャルの基本情報データベースを保存する。
        """

        if not isinstance(self._path, Path):
            raise PotentialsError(f"{self.__class__.__name__}.save: ")

        datas = {
            "アピール値": [
                {
                    "rare": RareClass(appeal.rare),
                    "level": appeal.level,
                    "potential": appeal.potential,
                }
                for appeal in self._appeals
            ],
            "特技発動率": [
                {
                    "rare": RareClass(ability.rare),
                    "level": ability.level,
                    "potential": ability.potential,
                }
                for ability in self._abilities
            ],
            "ライフ": [
                {
                    "rare": RareClass(life.rare),
                    "level": life.level,
                    "potential": life.potential,
                }
                for life in self._lives
            ],
        }

        with self._path.open(mode="w") as f:
            json.dump(datas, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    print(__file__)
