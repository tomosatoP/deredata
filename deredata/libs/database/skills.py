"""
エピソードの特技。

ほぼ更新はないが、マイスタイルアイドルの特技によって更新もありうる。

- ライブ中のスコア計算の ``特技倍率`` への特技効果（発動中）の加算方法
    | 切り上げは、小数点第3位で行う。
    | スコアアップ系列、コンボボーナス系列でそれぞれに、最も高い効果量が採用される。

    :math:`スコアアップ系列=スキルブースト系\\timesオルタネイト`

        スキルブースト系:
            :math:`1.00+切り上げ\\{スコアアップ効果量\\times(1.00+スコアアップ効果アップ効果量)\\}`

        オルタネイト:
            :math:`1.00+切り上げ\\{スコアアップ効果量\\times(1.00+オルタネイトによる効果量(極大))\\}`

    :math:`コンボボーナス系列=スキルブースト系\\timesミューチャル`

        スキルブースト系:
            :math:`1.00+切り上げ\\{コンボボーナス効果量\\times(1.00+コンボボーナス効果アップ効果量)\\}`

        ミューチャル:
            :math:`1.00+切り上げ\\{コンボボーナス効果量\\times(1.00+ミューチャルによる効果量(極大))\\}`

    特技効果コピーは、スキルブースト系（スコアアップ効果アップ、コンボボーナス効果アップ）として扱う。

        アンコール、リフレイン

    特技効果(極大)コピーは、スキルブースト系とは別系統として扱う。

        オルタネイト、ミューチャル

- センター効果レゾナンス（複数の特技が同時に発動中だった場合に効果が重複する）への対応
    | 切り上げは、小数点第3位で行う。
    | スコアアップ系列、コンボボーナス系列でそれぞれに、複数の特技の効果が重複して採用される。

    :math:`スコアアップ系列=スキルブースト系\\timesオルタネイト`

        スキルブースト系:
            :math:`1.0+切り上げ\\{\\sum{スコアアップ効果量}\\times(1.0+\\sum{スコアアップ効果アップ効果量})\\}`

        オルタネイト:
            :math:`1.0+切り上げ\\{\\sum{スコアアップ効果量}\\times(1.0+\\sum{オルタネイトによる効果量(極大)})\\}`

    :math:`コンボボーナス系列=スキルブースト系\\timesミューチャル`

        スキルブースト系:
            :math:`1.0+切り上げ\\{\\sum{コンボボーナス効果量}\\times(1.0+\\sum{コンボボーナス効果アップ効果量})\\}`

        ミューチャル:
            :math:`1.0+切り上げ\\{\\sum{コンボボーナス効果量}\\times(1.0+\\sum{ミューチャルによる効果量(極大)})\\}`


- ライブ中のスコア計算の ``特技倍率`` に関わらない特技効果の処理
    :ライフ回復: ライフで効果量がアップ（ライフスパークル）するので、``ライフ計算`` を行う。
    :ダメージガード: PERFECT のみフルコンボが前提なので、処理しない。（ただし、スキルブーストで、ライフ回復）
    :ライフ減少量ダウン: ``ライフ消費`` に影響するので、何らかの処理（未定）を行う。
    :ライフ消費: 特技効果の発動条件なので、``ライフ計算`` を行う。
    :PERFECTサポート: PERFECT のみフルコンボが前提なので、処理しない。
    :COMBO継続: PERFECT のみフルコンボが前提なので、処理しない。
    :集中: PERFECT のみフルコンボが前提なので、処理しない。

:class: TriggerType
:class: ProbabilityType
:class: DurationType
:class: BuffType
:class: IconType
:class: PerfectionType
:class: EffectType
:dataclass: Part
:dataclass: Skill
:class: Skills
:function: duration_value
:function: probability_value
"""

import json
from enum import StrEnum
from pathlib import Path
from dataclasses import dataclass, field

from deredata.libs.database.enumerations import IdolType, MusicType, UnitType
from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsSkillsLogger

# 特技データベースのファイルパス
SKILLSDB: str = database_folder() + "skills.json"
# マイスタイルアイドルの特技データベースのファイルパス
SKILLSDB_MYSTYLE: str = database_folder() + "skills_mystyle.json"


class SkillsError(Exception):
    """
    skillsのエラーハンドラ
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsSkillsLogger.error(f"SkillsError: {args}")


class SkillTriggerType(StrEnum):
    """
    特技発動要件の列挙クラス。

    :param str NA: "非該当"
    :param str SUBSTRACTLIFE_06: "ライフを6消費"
    :param str SUBSTRACTLIFE_09: "ライフを9消費"
    :param str SUBSTRACTLIFE_11: "ライフを11消費"
    :param str SUBSTRACTLIFE_15: "ライフを15消費"
    :param str SUBSTRACTLIFE_18: "ライフを18消費"
    :param str SUBSTRACTLIFE_25: "ライフを25消費"
    :param str SUBSTRACTLIFE_28: "ライフを28消費"
    :param str REFRAIN: "リフレイン"
    :param str ALTERNATE: "オルタネイト"
    :param str MUTUAL: "ミューチャル"
    :param str ENCORE: "アンコール"
    :param str MAGIC: "シンデレラマジック" - ユニット編成アイドル全員の特技効果を発動
    :param str NO_ENCORE_OR_MAGIC: "アンコール、シンデレラマジックで発動不可" - クリスタル・ヒール
    """

    NA = "非該当"
    SUBSTRACTLIFE_06 = "ライフを6消費"
    SUBSTRACTLIFE_09 = "ライフを9消費"
    SUBSTRACTLIFE_11 = "ライフを11消費"
    SUBSTRACTLIFE_15 = "ライフを15消費"
    SUBSTRACTLIFE_18 = "ライフを18消費"
    SUBSTRACTLIFE_25 = "ライフを25消費"
    SUBSTRACTLIFE_28 = "ライフを28消費"
    REFRAIN = "リフレイン"
    ALTERNATE = "オルタネイト"
    MUTUAL = "ミューチャル"
    ENCORE = "アンコール"
    MAGIC = "シンデレラマジック"
    NO_ENCORE_OR_MAGIC = "アンコール、シンデレラマジックで発動不可"


class ProbabilityType(StrEnum):
    """
    特技発動確率

    :param str NA: "非該当"
    :param str LOW: "低確率" - 30%
    :param str MIDDLE: "中確率" - 35%
    :param str HIGH: "高確率" - 40%
    """

    NA = "非該当"
    LOW = "低確率"
    MIDDLE = "中確率"
    HIGH = "高確率"


class DurationType(StrEnum):
    """
    特技継続時間

    :param str NA: "非該当"
    :param str TWO: "一瞬の間" - 2秒
    :param str THREE: "わずかな間" - 3秒
    :param str FOUR: "少しの間" - 4秒
    :param str FIVE: "しばらくの間" - 5秒
    :param str SIX: "かなりの間" - 6秒
    """

    ZERO = "非該当"
    TWO = "一瞬の間"
    THREE = "わずかな間"
    FOUR = "少しの間"
    FIVE = "しばらくの間"
    SIX = "かなりの間"


class PartType(StrEnum):
    """
    特技パーツ効果分類

    :param str NA: "非該当"
    :param str COMBO_SUPPORT: "COMBOサポート" - __でもCOMBO継続
    :param str PERFECT_SUPPORT: "PERFECTサポート" - __をPERFECTにする
    :param str LIFE_SUPPORT: "ライフサポート" - ライフを__回復
    :param str COMBO_BONUS: "COMBOボーナス" - COMBOボーナスアップ
    :param str SCORE_UP: "スコアアップ" - スコアアップ
    :param str SKILL_BOOST: "スキルブースト" - COMBOボーナス効果アップ、SOCOREアップ効果アップ
    :param str COPY: "適用" - アンコール、ミューチャル、リフレイン、オルタネイト
    :param str MAGIC: "シンデレラマジック" - シンデレラマジック
    """

    NA = "非該当"
    COMBO_SUPPORT = "COMBOサポート"
    PERFECT_SUPPORT = "PERFECTサポート"
    LIFE_SUPPORT = "ライフサポート"
    COMBO_BONUS = "COMBOボーナス"
    SCORE_UP = "スコアアップ"
    SKILL_BOOST = "スキルブースト"
    COPY = "適用"
    MAGIC = "シンデレラマジック"


class IconType(StrEnum):
    """
    適用アイコン

    :param str NA: "非該当"
    :param str ALL: "全アイコン"
    :param str SLIDE: "スライドアイコン"
    :param str FLICK: "フリックアイコン"
    :param str LONG: "ロングアイコン"
    """

    NA = "非該当"
    ALL = "全アイコン"
    SLIDE = "スライドアイコン"
    FLICK = "フリックアイコン"
    LONG = "ロングアイコン"


class PerfectionType(StrEnum):
    """
    適用判定

    :param str NA: "非該当"
    :param str NICE_BAD: "NICE/BAD判定"
    :param str NICE: "NICE判定"
    :param str ONLY_PERFECT: "PERFECT判定のみ"
    :param str GREAT_NICE_BAD: "GREAT/NICE/BAD判定"
    :param str GREAT_NICE: "GREAT/NICE判定"
    :param str GREAT: "GREAT判定"
    :param str PERFECT: "PERFECT判定"
    :param str PERFECT_GREAT: "PERFECT/GREAT判定"
    """

    NA = "非該当"
    NICE_BAD = "NICE/BAD判定"
    NICE = "NICE判定"
    ONLY_PERFECT = "PERFECT判定のみ"
    GREAT_NICE_BAD = "GREAT/NICE/BAD判定"
    GREAT_NICE = "GREAT/NICE判定"
    GREAT = "GREAT判定"
    PERFECT = "PERFECT判定"
    PERFECT_GREAT = "PERFECT/GREAT判定"


class EffectType(StrEnum):
    """
    特技パーツ効果

    :param str NA: "非該当"
    :param str CONCENTRATION: "集中" - PERFECT判定される時間が短くなる
    :param str BOOST_DOWN_DAMAGE: "ライフ減少量ダウンブースト" - ライフ減少量ダウン効果アップ｜ライフ計算
    :param str DOWN_DAMAGE: "ライフ減少量ダウン" - クリスタル・ヒール｜ライフ計算
    :param str ADD_RECOVERY: "ライフ回復付与" - ダメージガードにライフ回復を付与｜ライフ計算
    :param str BOOST_RECOVERY: "ライフ回復ブースト" - ライフ回復量アップ｜ライフ計算
    :param str RECOVERY: "ライフ回復" - **でライフを**回復｜ライフ計算
    :param str NO_DAMAGE: "ダメージガード" - ライフが減少しなくなる｜ライフ計算
    :param str COPY_BONUS_SCORE: "スコアボーナスコピー" - リフレイン
    :param str BONUS_SCORE: "スコアボーナス" - ｜特技倍率（スコア系）、アピール値、ライフ計算
    :param str COPY_BOOST_SCORE: "スコアブーストコピー" - ｜特技倍率（スコア系オルタネイト）
    :param str BOOST_SCORE: "スコアブースト" - ｜特技倍率（スコア系）、アイドル人数
    :param str MAGIC: "シンデレラマジック" - ユニット編成アイドル全員の特技効果を発動、最も高い効果を適用
    :param str ENCORE: "アンコール" - コピー
    :param str BOOST_SUPPORT_PERFECT: "PERFECTサポートブースト" - PERFECTサポート効果アップ
    :param str SUPPORT_PERFECT: "PERFECTサポート" - **をPERFECTにする
    :param str RECOVERY_AT_START: "LIVE開始時にライフ回復" - クリスタル・ヒール｜ライフ計算
    :param str COPY_BONUS_COMBO: "COMBOボーナスコピー" - リフレイン
    :param str BONUS_COMBO: "COMBOボーナス" - ｜特技倍率（COMBO系）、ライフ計算
    :param str COPY_BOOST_COMBO: "COMBOブーストコピー" - ｜特技倍率（COMBO系ミューチャル）
    :param str BOOST_COMBO: "COMBOブースト" - ｜特技倍率（COMBO系）、アイドル人数
    :param str BOOST_SUPPORT_COMBO: "COMBOサポートブースト" - COMBOサポート効果アップ
    :param str SUPPORT_COMBO: "COMBOサポート" - COMBO継続｜ライフ計算

    """

    NA = "非該当"
    CONCENTRATION = "集中"
    BOOST_DOWN_DAMAGE = "ライフ減少量ダウンブースト"
    DOWN_DAMAGE = "ライフ減少量ダウン"
    ADD_RECOVERY = "ライフ回復付与"
    BOOST_RECOVERY = "ライフ回復ブースト"
    RECOVERY = "ライフ回復"
    NO_DAMAGE = "ダメージガード"
    COPY_BONUS_SCORE = "スコアボーナスコピー"
    BONUS_SCORE = "スコアボーナス"
    COPY_BOOST_SCORE = "スコアブーストコピー"
    BOOST_SCORE = "スコアブースト"
    MAGIC = "シンデレラマジック"
    ENCORE = "アンコール"
    BOOST_SUPPORT_PERFECT = "PERFECTサポートブースト"
    SUPPORT_PERFECT = "PERFECTサポート"
    RECOVERY_AT_START = "LIVE開始時にライフ回復"
    COPY_BONUS_COMBO = "COMBOボーナスコピー"
    BONUS_COMBO = "COMBOボーナス"
    COPY_BOOST_COMBO = "COMBOブーストコピー"
    BOOST_COMBO = "COMBOブースト"
    BOOST_SUPPORT_COMBO = "COMBOサポートブースト"
    SUPPORT_COMBO = "COMBOサポート"


@dataclass(order=True, frozen=True)
class SkillPart:
    """
    特技パーツのデータクラス。

    :param str name: 特技パーツ（アクセスキー）。
    :param PartType parttype: 特技パーツ効果分類。
    :param IdolType member: 適用メンバー。
    :param IconType icon: 適用アイコン。
    :param PerfectionType perfection: 適用判定。
    :param EffectType effect: 特技パーツ効果。
    :param str | float value: 効果量、もしくは効果量タイプ説明。
    :param set[SkillPart] copy:
        適用（アンコール、リフレイン、オルタネイト、ミューチャル、シンデレラマジック）の特技パーツ集合。
    """

    name: str = "特技パーツ"
    parttype: PartType = field(default=PartType.NA, compare=False)
    member: IdolType = field(default=IdolType.NA, compare=False)
    icon: IconType = field(default=IconType.NA, compare=False)
    perfection: PerfectionType = field(default=PerfectionType.NA, compare=False)
    effect: EffectType = field(default=EffectType.NA, compare=False)
    value: str | float = field(default=0.0, compare=False)
    copy: set["SkillPart"] = field(default_factory=set, compare=False)


@dataclass(order=True, frozen=True)
class Skill:
    """
    特技のデータクラス。

    :param str name: 特技説明（アクセスキー）。
    :param str skill: 特技。
    :param str category: 特技分類。
    :param SkillTriggerType trigger: 発動要件。
    :param MusicType music: 楽曲要件。
    :param UnitType formation: 編成要件。
    :param int interval: 発動間隔（秒）。
    :param ProbabilityType probability: 発動確率。
    :param DurationType duration: 継続期間。
    :param set[SkillPart] skillparts: 特技パーツの集合。
    """

    name: str = "特技説明"
    skill: str = field(default="特技", compare=False)
    category: str = field(default="特技分類", compare=False)
    trigger: SkillTriggerType = field(default=SkillTriggerType.NA, compare=False)
    music: MusicType = field(default=MusicType.NA, compare=False)
    formation: UnitType = field(default=UnitType.NA, compare=False)
    interval: int = field(default=0, compare=False)
    probability: ProbabilityType = field(default=ProbabilityType.NA, compare=False)
    duration: DurationType = field(default=DurationType.ZERO, compare=False)
    skillparts: set[SkillPart] = field(default_factory=set, compare=False)


def duration_value(duration: DurationType) -> int:
    """
    継続期間を値に変換する。

    :return: 継続期間（秒）
    :rtype: int
    """

    match duration:
        case DurationType.TWO:
            return 2
        case DurationType.THREE:
            return 3
        case DurationType.FOUR:
            return 4
        case DurationType.FIVE:
            return 5
        case DurationType.SIX:
            return 6
        case _:
            return 0


def probability_value(probability: ProbabilityType) -> float:
    """
    特技発動確率を値に変換する。

    :return: 特技発動確率
    :rtype: float
    """

    match probability:
        case ProbabilityType.LOW:
            return 0.3
        case ProbabilityType.MIDDLE:
            return 0.35
        case ProbabilityType.HIGH:
            return 0.4
        case _:
            return 0.0


class Skills:
    """
    特技データベース。
    """

    _skills: set[Skill] = set()

    @property
    def categories(self) -> set[str]:

        return {skill.category for skill in self.__class__._skills}

    @property
    def skill_groupby_categories(self) -> dict[str, set[str]]:

        result: dict[str, set[str]] = dict()
        for category in self.categories:
            result |= {category: {skill.skill for skill in self.__class__._skills if skill.category == category}}

        return result

    def skills_by_category(self, category: str) -> set[str]:
        """
        特技分類から特技を取り出す。
        """

        return {skill.skill for skill in self.__class__._skills if skill.category == category}

    def get(self, name: str) -> Skill:
        """
        特技説明から特技の基本情報を取得する。

        :param str name: 特技説明

        :return: 特技の基本情報
        :rtype: Skill
        """

        result: set[Skill] = {skill for skill in self.__class__._skills if skill.name == name}
        return result.pop() if result else Skill()

    def gets(self) -> set[Skill]:
        return self.__class__._skills

    def add(self, skill: Skill) -> None:
        self.__class__._skills.add(skill)

    def remove(self, skill: Skill) -> None:
        self.__class__._skills.remove(skill)

    def update(self, after: Skill, before: Skill) -> None:
        """
        センター効果の基本情報の更新を行う。

        :param Buff after: 説明
        :param Buff before: 説明
        """
        if after.name != before.name:
            raise SkillsError(f"{self.__class__.__name__}.update: ")

        self.remove(before)
        self.add(after)

    @classmethod
    def load(cls, filename: str = SKILLSDB) -> None:
        """
        センター効果データベースの読み込みを行う。
        """

        path = Path(filename)
        if any([not isinstance(path, Path), not path.exists(), not path.is_file()]):
            raise SkillsError(f"{cls.__name__}.load: ")

        with path.open() as f:
            datas = json.load(f)

        for data in datas:
            skillparts = set()
            for skillpart in data["特技パーツ"]:
                skillpart = SkillPart(
                    name=skillpart["特技パーツ"],
                    parttype=skillpart["特技パーツ効果分類"],
                    member=IdolType(skillpart["適用メンバー"]),
                    icon=IconType(skillpart["適用アイコン"]),
                    perfection=PerfectionType(skillpart["適用判定"]),
                    effect=EffectType(skillpart["特技パーツ効果"]),
                    value=float(skillpart["効果量"]) if isinstance(skillpart["効果量"], float) else skillpart["効果量"],
                )
                skillparts.add(skillpart)

            skill = Skill(
                name=data["特技説明"],
                skill=data["特技"],
                category=data["特技分類"],
                trigger=SkillTriggerType(data["発動要件"]),
                music=MusicType(data["楽曲要件"]),
                formation=UnitType(data["編成要件"]),
                interval=int(data["発動間隔"]),
                probability=ProbabilityType(data["発動確率"]),
                duration=DurationType(data["継続期間"]),
                skillparts=skillparts,
            )
            cls._skills.add(skill)

        LibsSkillsLogger.info(f"{cls.__name__}.load: {len(cls._skills)}件の特技を読み込みました。")

    @classmethod
    def save(cls, filename: str = SKILLSDB) -> None:
        """
        センター効果データベースの保存を行う。
        """

        path: Path = Path(filename)
        if not isinstance(path, Path):
            raise SkillsError(f"{cls.__name__}.save: ")

        datas = [
            {
                "特技説明": skill.name,
                "特技": skill.skill,
                "特技分類": skill.category,
                "発動要件": SkillTriggerType(skill.trigger),
                "楽曲要件": MusicType(skill.music),
                "編成要件": UnitType(skill.formation),
                "発動間隔": int(skill.interval),
                "発動確率": ProbabilityType(skill.probability),
                "継続期間": DurationType(skill.duration),
                "特技パーツ": [
                    {
                        "特技パーツ": skillpart.name,
                        "特技パーツ効果分類": PartType(skillpart.parttype),
                        "適用メンバー": IdolType(skillpart.member),
                        "適用アイコン": IconType(skillpart.icon),
                        "適用判定": PerfectionType(skillpart.perfection),
                        "特技パーツ効果": EffectType(skillpart.effect),
                        "効果量": float(skillpart.value) if isinstance(skillpart.value, float) else skillpart.value,
                    }
                    for skillpart in sorted(skill.skillparts)
                ],
            }
            for skill in sorted(cls._skills)
        ]

        with path.open(mode="w") as f:
            json.dump(datas, f, ensure_ascii=False, indent=4)

        LibsSkillsLogger.info(f"{cls.__name__}: {len(cls._skills)}件の特技データベースを保存しました。")


class SkillsMystyle(Skills):
    """
    マイスタイルアイドル用の特技集。
    """

    _skills: set[Skill] = set()

    @classmethod
    def load(cls, filename: str = SKILLSDB_MYSTYLE) -> None:
        super().load(filename)

    @classmethod
    def save(cls, filename: str = SKILLSDB_MYSTYLE) -> None:
        super().save(filename)


if __name__ == "__main__":
    print(__file__)
