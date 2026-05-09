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
    """

    ruby: str = "ふりがな"  # ふりがな
    name: str = field(default="名前", compare=False)  # 名前
    type: IdolType = field(default=IdolType.CUTE, compare=False)  # アイドルタイプ
    life: int = field(default=0, compare=False)  # ライフ
    vocal: int = field(default=0, compare=False)  # ボーカル
    dance: int = field(default=0, compare=False)  # ダンス
    visual: int = field(default=0, compare=False)  # ビジュアル
    skill: int = field(default=0, compare=False)  # 特技


class Idols:
    """
    アイドル（``Idol``）の基本情報データベース。
    """

    def __init__(self) -> None:
        self._idols: set[Idol] = set()
        self._path: Path = Path(IDOLSDB)

    @property
    def filename(self) -> str:
        """
        アイドルの基本情報データベースのファイル名。
        """

        return self._path.name

    @filename.setter
    def filename(self, value: str) -> None:
        self._path = Path(value)

    def get(self, ruby: str) -> Idol:
        """
        アイドルのふりがなを条件にデータベースからアイドルの基本情報を取り出す。

        :param str ruby: 抽出条件のアイドルのふりがな。

        :return: アイドルのふりがなを条件に取り出した愛ルドの基本情報。
        :rtype: Idol
        """

        result: set[Idol] = {idol for idol in self._idols if idol.ruby == ruby}

        return result.pop() if result else Idol()

    def gets(self) -> set[Idol]:
        """
        データベースから全アイドルの基本情報を取り出す。

        :retunr: 全アイドルの基本情報。
        :rytpe: set[Idol]
        """

        return self._idols

    def add(self, idol: Idol) -> None:
        """
        データベースにアイドルの基本情報を追加する。

        :param Idol idol: 追加するアイドルの基本情報。
        """

        self._idols.add(idol)

    def remove(self, idol: Idol) -> None:
        """
        データベースのアイドルの基本情報を削除する。

        :param Idol idol: 削除するアイドルの基本情報。
        """

        self._idols.remove(idol)

    def update(self, after: Idol, before: Idol) -> None:
        """
        アイドルの基本情報の更新を行う。

        :param Idol after: 更新後のアイドルの基本情報。
        :param Idol before: 更新前のアイドルの基本情報。

        :raise IdolsError: **before** が、アイドルの基本情報データベースに存在しない。
        """
        if after.ruby != before.ruby:
            raise IdolsError(f"{self.__class__.__name__}.updata: ")

        self.remove(before)
        self.add(after)

    def load(self) -> None:
        """
        アイドル基本情報データベースの読み込みを行う。
        """
        if not isinstance(self._path, Path) or not self._path.exists():
            raise IdolsError(f"{self.__class__.__name__}.load: ")

        with self._path.open("r", encoding="utf-8-sig") as f:
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
            )
            self._idols.add(idol)

        LibsIdolsLogger.info(
            f"{self.__class__.__name__}.load: {len(self._idols)}件のアイドル基本情報を読み込みました。"
        )

    def save(self) -> None:
        """
        アイドル達の基本情報を保存する。
        """

        if not isinstance(self._path, Path):
            raise IdolsError(f"{self.__class__.__name__}.save: ")

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
            }
            for idol in sorted(self.gets())
        ]

        with self._path.open("w", encoding="utf-8") as f:
            json.dump(idols, f, indent=4, ensure_ascii=False)

        LibsIdolsLogger.info(f"{self.__class__.__name__}.save: アイドル基本情報データベースを保存しました。")


if __name__ == "__main__":
    print(__file__)
