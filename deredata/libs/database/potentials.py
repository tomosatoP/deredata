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

# ポテンシャルの基礎情報データベースのファイルパス。
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

    _appeals: list[Appeal] = []
    _abilities: list[Ability] = []
    _lives: list[Life] = []

    def value(self, type: str, rare: RareClass, level: int) -> float | int:
        """
        ポテンシャル補正値を取得する。

        :param str type: ポテンシャルタイプ ("ボーカル", "ダンス", "ビジュアル", "特技発動率", "ライフ")
        :param enums.RareClass rare: レア度
        :param int level: ポテンシャルレベル

        :return: ポテンシャル補正値。
        :type: float | int

        :todo: レア度、ポテンシャルレベルの入力値検査。
        """

        match type:
            case "ボーカル" | "ダンス" | "ビジュアル":
                return list(filter(lambda appeal: appeal.rare == rare, self.__class__._appeals))[level].potential
            case "特技発動率":
                return list(filter(lambda ability: ability.rare == rare, self.__class__._abilities))[level].potential
            case "ライフ":
                return list(filter(lambda life: life.rare == rare, self.__class__._lives))[level].potential
            case _:
                raise PotentialsError(f"{self.__class__.__name__}.value: Invalid type '{type}'")

    def add_appeal(self, appeal: Appeal) -> None:
        self.__class__._appeals.append(appeal)

    def add_ability(self, ability: Ability) -> None:
        self.__class__._abilities.append(ability)

    def add_life(self, life: Life) -> None:
        self.__class__._lives.append(life)

    def remove(self) -> None:
        LibsPotentialsLogger.error(f"{self.__class__.__name__}.remove: 未実装。")

    @classmethod
    def _clear(cls) -> None:
        """
        ポテンシャルの基本情報データベースを初期化する。
        """

        cls._appeals.clear()
        cls._abilities.clear()
        cls._lives.clear()

    @classmethod
    def load(cls, filename: str = POTENTIALSDB) -> None:
        """
        ポテンシャルの基本情報データベースを読み込む。
        """

        path = Path(filename)
        if not isinstance(path, Path) or not path.exists() or not path.is_file():
            raise PotentialsError(f"{cls.__name__}.load: ")

        cls._clear()
        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)

            for appeal in data["アピール値"]:
                cls._appeals.append(
                    Appeal(
                        rare=RareClass(appeal["rare"]),
                        level=appeal["level"],
                        potential=appeal["potential"],
                    )
                )
            for ability in data["特技発動率"]:
                cls._abilities.append(
                    Ability(
                        rare=RareClass(ability["rare"]),
                        level=ability["level"],
                        potential=ability["potential"],
                    )
                )
            for life in data["ライフ"]:
                cls._lives.append(
                    Life(
                        rare=RareClass(life["rare"]),
                        level=life["level"],
                        potential=life["potential"],
                    )
                )

        number: int = len(cls._appeals) + len(cls._abilities) + len(cls._lives)
        LibsPotentialsLogger.info(f"{cls.__name__}.load: {number}件のポテンシャルデータを読み込みました。")

    @classmethod
    def save(cls, fileanem: str = POTENTIALSDB) -> None:
        """
        ポテンシャルの基本情報データベースを保存する。
        """

        path: Path = Path(fileanem)
        if not isinstance(path, Path):
            raise PotentialsError(f"{cls.__name__}.save: ")

        datas = {
            "アピール値": [
                {
                    "rare": RareClass(appeal.rare),
                    "level": appeal.level,
                    "potential": appeal.potential,
                }
                for appeal in cls._appeals
            ],
            "特技発動率": [
                {
                    "rare": RareClass(ability.rare),
                    "level": ability.level,
                    "potential": ability.potential,
                }
                for ability in cls._abilities
            ],
            "ライフ": [
                {
                    "rare": RareClass(life.rare),
                    "level": life.level,
                    "potential": life.potential,
                }
                for life in cls._lives
            ],
        }

        with path.open(mode="w") as f:
            json.dump(datas, f, ensure_ascii=False, indent=4)

        number: int = len(cls._appeals) + len(cls._abilities) + len(cls._lives)
        LibsPotentialsLogger.info(f"{cls.__name__}.save: {number}件のポテンシャルデータを保存しました。")


if __name__ == "__main__":
    print(__file__)
