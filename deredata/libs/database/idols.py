"""
アイドル達の基本情報を扱うモジュール。

:dataclass Idol: アイドルの基本情報（名前、ポテンシャルなど）のデータクラス。
:class Idols: アイドル達の基本情報データベース。
"""

import json
from pathlib import Path
from dataclasses import dataclass, field

from deredata.libs.database.enumerations import IdolType
from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsIdolsLogger

IDOLSDB: str = database_folder() + "idols.json"


class IdolsError(Exception):
    """
    idolsのエラーハンドラ
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsIdolsLogger.error(f"IdolsError: {args}")


@dataclass(order=True, frozen=True)
class Idol:
    """
    アイドルの基本情報のデータクラス。

    :param str ruby: ふりがな（アクセスキー）
    :param str name: 名前
    :param enums.IdolType type: アイドルタイプ
    :param int life: ライフポテンシャルレベル
    :param int vocal: ボーカルポテンシャルレベル
    :param int dance: ダンスポテンシャルレベル
    :param int visual: ビジュアルポテンシャルレベル
    :param int skill: 特技ポテンシャルレベル
    :param int over: 未配分のポテンシャル
    """

    ruby: str = "ふりがな"  # ふりがな
    name: str = field(default="名前", compare=False)  # 名前
    type: IdolType = field(default=IdolType.CUTE, compare=False)  # アイドルタイプ
    life: int = field(default=0, compare=False)  # ライフ
    vocal: int = field(default=0, compare=False)  # ボーカル
    dance: int = field(default=0, compare=False)  # ダンス
    visual: int = field(default=0, compare=False)  # ビジュアル
    skill: int = field(default=0, compare=False)  # 特技
    over: int = field(default=0, compare=False)  # 余り


class Idols:
    """
    アイドル（``Idol``）の基本情報データベース。
    """

    _idols: set[Idol] = set()

    def get(self, ruby: str) -> Idol:
        """
        アイドルのふりがなを条件にデータベースからアイドルの基本情報を取り出す。

        :param str ruby: 抽出条件のアイドルのふりがな。

        :return: アイドルのふりがなを条件に取り出した愛ルドの基本情報。
        :rtype: Idol
        """

        result: set[Idol] = {idol for idol in self.__class__._idols if idol.ruby == ruby}

        return result.pop() if result else Idol()

    def gets(self) -> set[Idol]:
        """
        データベースから全アイドルの基本情報を取り出す。

        :retunr: 全アイドルの基本情報。
        :rytpe: set[Idol]
        """

        return self.__class__._idols

    def add(self, idol: Idol) -> None:
        """
        データベースにアイドルの基本情報を追加する。

        :param Idol idol: 追加するアイドルの基本情報。
        """

        self.__class__._idols.add(idol)

    def remove(self, idol: Idol) -> None:
        """
        データベースのアイドルの基本情報を削除する。

        :param Idol idol: 削除するアイドルの基本情報。
        """

        self.__class__._idols.remove(idol)

    def update(self, after: Idol, before: Idol) -> None:
        """
        アイドルの基本情報の更新を行う。

        :param Idol after: 更新後のアイドルの基本情報。
        :param Idol before: 更新前のアイドルの基本情報。

        :raise IdolsError: **after** と **before** で、アイドルのふりがなが一致しなかった。
        """
        if after.ruby != before.ruby:
            raise IdolsError(f"{self.__class__.__name__}.updata: 更新できませんでした。")

        self.remove(before)
        self.add(after)

    @classmethod
    def load(cls, filename: str = IDOLSDB) -> None:
        """
        アイドル基本情報データベースの読み込みを行う。

        :param str filename: 初期値は、既定のファイル名。

        :raise IdolsError: アイドル基本情報データベースを読み込めなかった。
        """

        path = Path(filename)
        if any([not isinstance(path, Path), not path.exists(), not path.is_file()]):
            raise IdolsError(f"{cls.__name__}.load: アイドル基本情報データベースを読み込めませんでした。")

        if not len(cls._idols):
            cls._idols.clear()

        with path.open("r", encoding="utf-8-sig") as f:
            datas = json.load(f)

        for data in datas:
            idol = Idol(
                ruby=data["ふりがな"],
                name=data["名前"],
                type=IdolType(data["アイドルタイプ"]),
                life=int(data["ライフ"]),
                vocal=int(data["ボーカル"]),
                dance=int(data["ダンス"]),
                visual=int(data["ビジュアル"]),
                skill=int(data["特技"]),
                over=int(data["余り"]),
            )
            cls._idols.add(idol)

        LibsIdolsLogger.info(
            f"{cls.__name__}.load: {len(cls._idols)}件のアイドル基本情報データベースを読み込みました。"
        )

    @classmethod
    def save(cls, filename: str = IDOLSDB) -> None:
        """
        アイドル達の基本情報を保存する。

        :param str filename: 初期値は、既定のファイル名。

        :raise IdolsError: アイドル基本情報データベースを保存できなかった。
        """

        path = Path(filename)
        if not isinstance(path, Path):
            raise IdolsError(f"{cls.__name__}.save: アイドル基本情報データベースを保存できませんでした。")

        idols = [
            {
                "ふりがな": idol.ruby,
                "名前": idol.name,
                "アイドルタイプ": IdolType(idol.type),
                "ライフ": int(idol.life),
                "ボーカル": int(idol.vocal),
                "ダンス": int(idol.dance),
                "ビジュアル": int(idol.visual),
                "特技": int(idol.skill),
                "余り": int(idol.over),
            }
            for idol in sorted(cls._idols)
        ]

        with path.open("w", encoding="utf-8") as f:
            json.dump(idols, f, indent=4, ensure_ascii=False)

        LibsIdolsLogger.info(f"{cls.__name__}.save: {len(cls._idols)}件のアイドル基本情報データベースを保存しました。")


if __name__ == "__main__":
    print(__file__)
