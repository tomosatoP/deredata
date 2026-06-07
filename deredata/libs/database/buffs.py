"""
エピソードのセンター効果のモジュール。

センター効果データベース、マイスタイルアイドル用のセンター効果データベースを扱う。
ほぼ更新はないが、マイスタイルアイドルのセンター効果によって更新もありうる。

:class BuffTriggerType: センター効果・発動要件の列挙クラス。
:class BuffPartTriggerType: センター効果パーツ・適用要件列挙クラス。
:class AppealType: センター効果パーツ・適用アピールの列挙クラス。
:dataclass BuffPart: センター効果パート情報のデータクラス。
:dataclass Buff: センター効果の基本情報のデータクラス。
:class Buffs: センター効果データベース。
:class BuffsMystyle: マイスタイルアイドル用のセンター効果データベース。
"""

import json
from enum import StrEnum
from pathlib import Path
from dataclasses import dataclass, field

from deredata.libs.database.enumerations import IdolType, MusicType, UnitType
from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsBuffsLogger

# センター効果情報データベースのファイル名
BUFFSDB: str = database_folder() + "buffs.json"
BUFFSDB_MYSTYLE: str = database_folder() + "buffs_mystyle.json"


class BuffsError(Exception):
    """
    buffsのエラーハンドラ
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsBuffsLogger.error(f"BuffsError: {args}")


class BuffTriggerType(StrEnum):
    """
    センター効果・発動要件の列挙クラス。

      :NA: 非該当
      :CLEAR_LIVE: LIVEクリア
    """

    NA = "非該当"
    CLEAR_LIVE = "LIVEクリア"  # スコア計算に関わらないので、アピール値計算に使わない。


class BuffPartTriggerType(StrEnum):
    """
    センター効果パーツ・適用要件列挙クラス。

      :NA: 非該当
      :OPEN_FACE: フェイスオープン
      :MIDDLE: 中確率
    """

    NA = "非該当"
    OPEN_FACE = "フェイスオープン"
    MIDDLE = "中確率"


class AppealType(StrEnum):
    """
    センター効果パーツ・適用アピールの列挙クラス。

      :NA: 非該当
      :ALL: 全アピール値
      :VOCAL: ボーカルアピール値
      :DANCE: ダンスアピール値
      :VISUAL: ビジュアルアピール値
      :LIFE: ライフ
      :ABILITY: 特技発動確率
      :BLESS: シンデレラブレス（全員のセンター効果を発揮し、最も高い効果を適用）
      :RESONANCE: レゾナンス（全ての特技効果が重複時に加算）
      :TYPEMATCH: タイプ一致
      :STARPIECE: スターピース
      :EXP: 獲得経験値
      :FANS: 獲得ファン数
      :STAREMBLEM: スターエンブレム
      :MONEYS: マニー
      :FREINDSHIP: 友情pt
      :REWARD: 特別報酬
    """

    NA = "非該当"
    ALL = "全アピール値"
    VOCAL = "ボーカルアピール値"
    DANCE = "ダンスアピール値"
    VISUAL = "ビジュアルアピール値"
    LIFE = "ライフ"
    ABILITY = "特技発動確率"
    BLESS = "シンデレラブレス"  # 全員のセンター効果を発揮し、最も高い効果を適用
    RESONANCE = "レゾナンス"  # 全ての特技効果が重複時に加算
    TYPEMATCH = "タイプ一致"
    STARPIECE = "スターピース"  # これより下はスコア計算に関わらないので、アピール値計算に使わない。
    EXP = "獲得経験値"
    FANS = "獲得ファン数"
    STAREMBLEM = "スターエンブレム"
    MONEYS = "マニー"
    FREINDSHIP = "友情pt"
    REWARD = "特別報酬"


@dataclass(order=True, frozen=True)
class BuffPart:
    """
    センター効果パート情報のデータクラス。

    :param str name: センター効果パーツ（ソート対象）
    :param BuffPartTriggerType trigger: 適用要件
    :param MusicType music: 適用楽曲
    :param IdolType member: 適用メンバー
    :param AppealType appeal: 適用効果
    :param float value: 効果量
    """

    name: str = "センター効果パーツ"  # センター効果パーツ
    trigger: BuffPartTriggerType = field(default=BuffPartTriggerType.NA, compare=False)  # 適用要件
    music: MusicType = field(default=MusicType.NA, compare=False)  # 適用楽曲
    member: IdolType = field(default=IdolType.NA, compare=False)  # 適用メンバー
    appeal: AppealType = field(default=AppealType.NA, compare=False)  # 適用効果
    value: float = field(default=0, compare=False)  # 効果量


@dataclass(order=True, frozen=True)
class Buff:
    """
    センター効果の基本情報のデータクラス。

    :param str name: センター効果説明（ソート対象）
    :param str buff: センター効果
    :param str category: センター効果分類
    :param str categoryname: センター効果分類説明
    :param BuffTriggerType trigger: 発動要件
    :param UnitType formation: 編成要件
    :param MusicType music: 楽曲要件
    :param set[BuffPart] buffparts: センター効果パーツの集合
    """

    name: str = "センター効果説明"  # センター効果説明
    buff: str = field(default="センター効果", compare=False)  # センター効果
    category: str = field(default="センター効果分類", compare=False)  # センター効果分類
    categoryname: str = field(default="センター効果分類説明", compare=False)
    trigger: BuffTriggerType = field(default=BuffTriggerType.NA, compare=False)  # 発動要件
    formation: UnitType = field(default=UnitType.NA, compare=False)  # 編成要件
    music: MusicType = field(default=MusicType.NA, compare=False)  # 楽曲要件
    buffparts: set[BuffPart] = field(default_factory=set, compare=False)  # 集合（ センター効果パーツ）


class Buffs:
    """
    センター効果データベース。
    """

    _buffs: set[Buff] = set()

    @property
    def categories(self) -> set[str]:
        """
        センター効果分類の集合。
        """

        return {buff.category for buff in self.__class__._buffs}

    @property
    def categorynames(self) -> set[str]:
        """
        センター効果分類説明の集合。
        """

        return {buff.categoryname for buff in self.__class__._buffs}

    @property
    def buff_groupby_categorynames(self) -> dict[str, set[str]]:
        """
        センター効果分類説明をキーとするセンター効果のマッピング。
        """

        result: dict[str, set[str]] = dict()
        for categoryname in sorted(self.categorynames):
            result |= {categoryname: {buff.buff for buff in self.__class__._buffs if buff.categoryname == categoryname}}

        return result

    def buffs_by_categoryname(self, categoryname: str) -> set[str]:
        """
        センター効果分類説明を条件にセンター効果を取り出す。

        :param str categoryname: 抽出条件のセンター効果分類説明。

        :return: センター効果分類説明を条件に取り出したセンター効果の集合。
        :rtype: set[str]
        """

        return {buff.buff for buff in self.__class__._buffs if buff.categoryname == categoryname}

    def get(self, name: str) -> Buff:
        """
        センター効果説明を条件にセンター効果の基本情報を取得する。

        :param str name: 抽出条件のセンター効果説明。

        :return: センター効果説明を条件に取り出されたセンター効果の基本情報。
        :rtype: Buff
        """

        result = {buff for buff in self.__class__._buffs if buff.name == name}
        return result.pop() if result else Buff()

    def gets(self) -> set[Buff]:
        """
        センター効果の基本情報の集合を取得する。

        :return: センター効果の基本情報の集合。
        :rtype: set[Buff]
        """

        return self.__class__._buffs

    def add(self, buff: Buff) -> None:
        """
        センター効果の基本情報をセンター効果データベースに追加する。

        :param Buff buff: 追加するセンター効果の基本情報。
        """

        self.__class__._buffs.add(buff)

    def remove(self, buff: Buff) -> None:
        """
        センター効果の基本情報をセンター効果データベースから削除する。

        :param Buff buff: 削除するセンター効果の基本情報。
        """

        self.__class__._buffs.remove(buff)

    def update(self, after: Buff, before: Buff) -> None:
        """
        センター効果の基本情報の更新を行う。

        :param Buff after: 更新前のセンター効果の基本情報。
        :param Buff before: 更新後のセンター効果の基本情報。

        :raise BuffError: **before** （更新前のセンター効果の基本情報）がセンター効果データベースに存在しない。
        """

        if after.name != before.name:
            raise BuffsError(f"{self.__class__.__name__}.update: ")

        self.remove(before)
        self.add(after)

    @classmethod
    def load(cls, filename: str = BUFFSDB) -> None:
        """
        センター効果データベースの読み込みを行う。
        """

        path = Path(filename)
        if any([not isinstance(path, Path), not path.exists(), not path.is_file()]):
            raise BuffsError(f"{cls.__name__}.load: ")

        with path.open() as f:
            datas = json.load(f)

        for data in datas:
            buffparts = set()
            for buffpart in data["センター効果パーツ"]:
                buffpart = BuffPart(
                    name=buffpart["センター効果パーツ"],
                    trigger=BuffPartTriggerType(buffpart["適用要件"]),
                    music=MusicType(buffpart["適用楽曲"]),
                    member=IdolType(buffpart["適用メンバー"]),
                    appeal=AppealType(buffpart["適用効果"]),
                    value=float(buffpart["効果量"]),
                )
                buffparts.add(buffpart)

            buff = Buff(
                name=data["センター効果説明"],
                buff=data["センター効果"],
                category=data["センター効果分類"],
                categoryname=data["センター効果分類説明"],
                trigger=BuffTriggerType(data["発動要件"]),
                formation=UnitType(data["編成要件"]),
                music=MusicType(data["楽曲要件"]),
                buffparts=buffparts,
            )
            cls._buffs.add(buff)

        LibsBuffsLogger.info(f"{cls.__name__}.load: {len(cls._buffs)}件のセンター効果を読み込みました。")

    @classmethod
    def save(cls, filename: str = BUFFSDB) -> None:
        """
        センター効果データベースの保存を行う。
        """

        path: Path = Path(filename)
        if not isinstance(path, Path):
            raise BuffsError(f"{cls.__name__}.save: ")

        datas = [
            {
                "センター効果説明": buff.name,
                "センター効果": buff.buff,
                "センター効果分類": buff.category,
                "センター効果分類説明": buff.categoryname,
                "発動要件": BuffTriggerType(buff.trigger),
                "編成要件": UnitType(buff.formation),
                "楽曲要件": MusicType(buff.music),
                "センター効果パーツ": [
                    {
                        "センター効果パーツ": buffpart.name,
                        "適用要件": BuffPartTriggerType(buffpart.trigger),
                        "適用楽曲": MusicType(buffpart.music),
                        "適用メンバー": IdolType(buffpart.member),
                        "適用効果": AppealType(buffpart.appeal),
                        "効果量": float(buffpart.value),
                    }
                    for buffpart in sorted(buff.buffparts)
                ],
            }
            for buff in sorted(cls._buffs)
        ]

        with path.open(mode="w") as f:
            json.dump(datas, f, ensure_ascii=False, indent=4)

        LibsBuffsLogger.info(f"{cls.__name__}.save:  {len(cls._buffs)}件のセンター効果データベースを保存しました。")


class BuffsMystyle(Buffs):
    """
    マイスタイルアイドル用のセンター効果データベース。
    """

    _buffs: set[Buff] = set()

    @classmethod
    def load(cls, filename: str = BUFFSDB_MYSTYLE) -> None:
        super().load(filename)

    @classmethod
    def save(cls, filename: str = BUFFSDB_MYSTYLE) -> None:
        super().save(filename)


if __name__ == "__main__":
    print(__file__)
