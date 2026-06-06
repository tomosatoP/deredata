"""
デレステのライブのユニットを扱うモジュール。

ゲスト有のユニット（6人編成）
ゲスト無しのユニット（5人編成）
グランドライブのユニット（5人編成a、5人編成b、5人編成c）

:dataclass Position6: 6人編成ユニットのデータクラス。
:dataclass Position5: 5人編成ユニットデータクラス。
:dataclass Unit: 通常ライブのユニットのデータクラス。
:dataclass GrandliveUnit: グランドライブのユニットのデータクラス。
:class Units: ユニット情報データベースのクラス。
"""

import json
from typing import Any
from pathlib import Path
from dataclasses import dataclass, field

from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsUnitsLogger

# ユニット情報データベースのファイルパス
UNITSDB: str = database_folder() + "units.json"


class UnitsError(Exception):
    """
    unitsのエラーハンドラ
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsUnitsLogger.error(f"UnitsError: {args}")


@dataclass
class Positions6:
    """
    ゲスト有りユニット（6人編成）のデータクラス。

    :param str centerposition: センターのエピソード名
    :param str leftposition: 左隣りのエピソード名
    :param str rightposition: 右隣りのエピソード名
    :param str leftendposition: 左端のエピソード名
    :param str rightendposition: 右端のエピソード名
    :param str guestposition: ゲストのエピソード名
    """

    centerposition: str = "センター"
    leftposition: str = "左隣り"
    rightposition: str = "右隣り"
    leftendposition: str = "左端"
    rightendposition: str = "右端"
    guestposition: str = "ゲスト"

    def list(self) -> list[str]:
        return [
            self.centerposition,
            self.leftposition,
            self.rightposition,
            self.leftendposition,
            self.rightendposition,
            self.guestposition,
        ]


@dataclass
class Positions5:
    """
    ゲスト無しユニット（5人編成）のデータクラス。

    :param str centerposition: センターのエピソード名
    :param str leftposition: 左隣りのエピソード名
    :param str rightposition: 右隣りのエピソード名
    :param str leftendposition: 左端のエピソード名
    :param str rightendposition: 右端のエピソード名
    """

    centerposition: str = "センター"
    leftposition: str = "左隣り"
    rightposition: str = "右隣り"
    leftendposition: str = "左端"
    rightendposition: str = "右端"

    def list(self) -> list[str]:
        return [
            self.centerposition,
            self.leftposition,
            self.rightposition,
            self.leftendposition,
            self.rightendposition,
        ]


@dataclass(order=True, frozen=True)
class Unit:
    """
    通常ライブのユニットのデータクラス。

    :param str name: ユニット名
    :param Position6 positions: ユニットのメンバー
    """

    name: str = "ユニット"
    positions: Positions6 = field(default_factory=Positions6, compare=False)


@dataclass(order=True, frozen=True)
class GrandliveUnit:
    """
    グランドライブのユニットのデータクラス。

    :param str name: ユニット名
    :param Position5 unita: ユニットaのメンバー
    :param Position5 unitb: ユニットbのメンバー
    :param Position5 unitc: ユニットcのメンバー
    """

    name: str = "グランドライブユニット"
    unita: Positions5 = field(default_factory=Positions5, compare=False)
    unitb: Positions5 = field(default_factory=Positions5, compare=False)
    unitc: Positions5 = field(default_factory=Positions5, compare=False)


class Units:
    """
    ユニット情報データベース。
    """

    _units: set[Unit | GrandliveUnit] = set()

    def get(self, name: str) -> Unit | GrandliveUnit:
        """
        get

        :param str name: 抽出条件のユニット名。
        """

        result: set[Unit | GrandliveUnit] = {unit for unit in Units._units if unit.name == name}
        return result.pop() if result else Unit()

    def gets(self) -> set[Unit | GrandliveUnit]:
        """
        gets

        :return: 全ユニットの集合
        :rtype: set[Unit]
        """

        return Units._units

    def add(self, unit: Unit | GrandliveUnit) -> None:
        """
        通常ライブもしくはグランドライブのユニットをユニット情報データベースに追加する。

        :param Unit | GrandliveUnit unit: 追加する通常ライブもしくはグランドライブのユニット。
        """

        Units._units.add(unit)

    def remove(self, unit: Unit | GrandliveUnit) -> None:
        """
        通常ライブもしくはグランドライブのユニットをユニット情報データベースから削除する。

        :param Unit | GrandliveUnit unit: 削除する通常ライブもしくはグランドライブのユニット。
        """

        Units._units.remove(unit)

    def update(self, after: Unit | GrandliveUnit, before: Unit | GrandliveUnit) -> None:
        """
        ユニットの基本情報の更新を行う。

        :param Idol after: 説明
        :param Idol before: 説明
        """
        if after.name != before.name:
            raise UnitsError(f"{self.__class__.__name__}.updata: ユニット名が異なるので、更新できません。")

        self.remove(before)
        self.add(after)

    @classmethod
    def load(cls, filename: str = UNITSDB) -> None:
        """
        ユニット情報データベースの読み込みを行う。

        :param str filename: 初期値は、既定のファイル名。
        """

        path = Path(filename)
        if any([not isinstance(path, Path), not path.exists(), not path.is_file()]):
            raise UnitsError(f"{cls.__name__}.load: {filename} を読み込めませんでした。")

        with path.open("r", encoding="utf-8-sig") as f:
            datas = json.load(f)

        for data in datas:
            if data["タイプ"] == "ユニット":
                members = Positions6(
                    centerposition=data["メンバー"][0]["センター"],
                    leftposition=data["メンバー"][0]["左隣り"],
                    rightposition=data["メンバー"][0]["右隣り"],
                    leftendposition=data["メンバー"][0]["左端"],
                    rightendposition=data["メンバー"][0]["右端"],
                    guestposition=data["メンバー"][0]["ゲスト"],
                )
                unit = Unit(
                    name=data["名前"],
                    positions=members,
                )
                cls._units.add(unit)

            elif data["タイプ"] == "グランドライブユニット":
                grandliveunit = GrandliveUnit()
                cls._units.add(grandliveunit)
            else:
                raise UnitsError(f"{cls.__name__}.load: {data['名前']} を読み込めませんでした。")

        LibsUnitsLogger.info(f"{cls.__name__}.load: {len(cls._units)}件のユニット情報を読み込みました。")

    @classmethod
    def save(cls, filename: str = UNITSDB) -> None:
        """
        ユニット情報データベースを保存する。

        :param str filename: 初期値は、既定のファイル名。
        """

        units: list[dict[str, Any]] = list()

        path = Path(filename)
        if not isinstance(path, Path):
            raise UnitsError(f"{cls.__name__}.save: {filename} を保存できません。")

        for unit in sorted(cls._units):
            if isinstance(unit, Unit):
                units.append(
                    {
                        "タイプ": "ユニット",
                        "名前": unit.name,
                        "メンバー": [
                            {
                                "センター": unit.positions.centerposition,
                                "左隣り": unit.positions.leftposition,
                                "右隣り": unit.positions.rightposition,
                                "左端": unit.positions.leftendposition,
                                "右端": unit.positions.rightendposition,
                                "ゲスト": unit.positions.guestposition,
                            }
                        ],
                    }
                )
            elif isinstance(unit, GrandliveUnit):
                pass
            else:
                raise UnitsError(f"{cls.__name__}.save: {unit.name} を保存できません。")

        with path.open("w", encoding="utf-8") as f:
            json.dump(units, f, indent=4, ensure_ascii=False)

        LibsUnitsLogger.info(f"{cls.__name__}.save: ユニット情報データベースを保存しました。")


if __name__ == "__main__":
    print(__file__)
