"""
デレステの ``スコア計算`` を扱うモジュール。

``アピール値計算モジュール`` で求めたアピール値からスコアをシミュレートする。
まずは、通常のゲストメンバー有りの ``WIDEライブ`` に対応する。
``GrandLive`` や ``LiveCarnival（Booth効果）`` にも対応したい。

:入力:
    | デレステ譜面データのファイル名
    | レゾナンスの適否
    | ゲストを含むユニットメンバーのエピソード名リスト
    | ゲストを含むユニットメンバーのアピール値（ボーカル・ダンス・ビジュアル）
    | ゲストを含むユニットメンバーのライフ
    | ユニットメンバーの特技発動確率
    | ユニットメンバーの特技継続期間
    | サポートメンバーのエピソード名リスト。*LiveCarnivalでは、不要。*
    | サポートメンバーのアピール値（ボーカル・ダンス・ビジュアル）。*LiveCarnivalでは、不要。*

:出力:
    ノートごとのスコアリスト

スコア計算の流れ

:スコア計算:
    :math:`\\displaystyle \\sum^{ノート}{スコア}`

:ノートのスコア計算:
    :math:`基礎値\\times判定倍率\\timesコンボ倍率\\times特技倍率`

:ノートの基礎値計算:
    :math:`\\displaystyle \\frac{曲係数\\times\\displaystyle \\sum^{ゲストを含むユニットメンバーとサポートメンバー}\
        {アピール値}}{ノート総数}`

:ノートの判定倍率計算:
    - PERFECT判定=1.0
    - GREAT判定=0.7
    - NICE判定=0.4
    - BAD判定=0.1
    - MISS判定=0.0

:ノートのコンボ倍率計算:
    総ノート数に対するコンボ数の割合によって決まる倍率。

:ノートの特技倍率計算:
    :math:`\\displaystyle \\prod^{特技系統}{(1.00+特技倍率)}`

    特技系統（スコアアップ系、COMBOボーナス系、オルタネイト系、ミューチャル系）ごとに最大効果を、小数点第二位で切り上げる。
    
    センター効果・レゾナンス有効時は、発動している特技で効果を（特技系統ごとに）総和する。

:スコアアップ系:
    :math:`スコアアップ効果量\\times(1.00+スコアアップ効果アップ効果量)`

    :math:`ミューチャルのスコアボーナスダウン量\\times(1.00+0.00)`

:COMBOボーナス系:
    :math:`コンボボーナス効果量\\times(1.00+コンボボーナス効果アップ効果量)`

    :math:`オルタネイトのCOMBOボーナスダウン量\\times(1.00+0.00)`

:オルタネイト:
    :math:`コピーしたスコアアップ効果量\\times(1.00+0.70)`

:ミューチャル:
    :math:`コピーしたCOMBOボーナス効果量\\times(1.00+0.70)`
"""

import numpy as np
from functools import reduce, partial, wraps
from typing import Callable, Any
from operator import mul
from random import seed, random
from math import ceil
from fractions import Fraction
from dataclasses import dataclass, field
from enum import IntEnum

from deredata.libs.database.musics import FPS, Note, NoteType, SongType, Music
from deredata.libs.database.enumerations import IdolType, DominantType, MusicType, UnitType
from deredata.libs.database.episodes import Episode, Episodes
from deredata.libs.database.skills import Skill, Skills, SkillPart, IconType
from deredata.libs.database.musiclevels import MusicLevels
from deredata.libs.database.comborates import ComboRates
from deredata.libs.database.motif import Motives
from deredata.libs.database.dominant import Dominants
from deredata.libs.database.lifesparkle import Lifesparkles

from kivy.logger import Logger as LibsStageLogger

UNIT_SIZE: int = 5  # とりあえず5人固定で実装


class StageError(Exception):
    """Stageモジュールのエラーハンドラ"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsStageLogger.error(f"StageError: {args}")


class IndicesSkillCategoryElement(IntEnum):
    """
    特技系統の要素の列挙クラス。特技効果量リストもしくは配列の添え字に相当する。

    :param 0 BONUS: ボーナス。
    :param 1 BOOST: ブースト。
    """

    BONUS = 0
    BOOST = 1


class IndicesSkillCategory(IntEnum):
    """
    特技系統の列挙クラス。特技効果量リストもしくは配列の添え字に相当する。

    :param 0 SCORE: スコアアップ系（ミューチャル・スコアダウンも含む）。
    :param 1 COMBO: COMBOボーナス系（オルタネイト・COMBOダウンも含む）。
    :param 2 ALTERNATE: オルタネイト系。
    :param 3 MUTUAL: ミューチャル系。
    """

    SCORE = 0
    COMBO = 1
    ALTERNATE = 2
    MUTUAL = 3


@dataclass
class TimeTable:
    """
    特技発動時間割の基礎情報のデータクラス。

    :param bool active: 特技の発動不発。``True`` 時は発動、``False`` 時は不発。
    :param int start: time_base 当たりの特技発動開始時間。
    :param int end: time_base 当たりの特技発動終了時間。
    :param fraction time_base: 単位時間（1/FPS秒）。
    """

    active: bool = False  # 特技が発動か不発か。
    start: int = 0  # 特技の開始時間。
    end: int = 0  # 特技の終了時間。
    time_base: Fraction = Fraction(1, FPS)  # 単位時間。


@dataclass
class Life:
    """
    ライフ値のデータクラス。

    ライフ値は、初期ライフ値の2倍が上限(limit)で、0 を下回る処理は許されていない 。

    :param int value: ライフ値、もしくは残ライフ値。
    """

    value: int = 1  # ライフ値、もしくは残ライフ値。
    limit: int = field(init=False)  # ライフ値の上限。

    def __post_init__(self) -> None:
        self.limit = self.value * 2

    def update(self, value: int) -> bool:
        """
        ライフ値の計算（加算・減算）。

        | 上限：結果が上限（limit）を上回る場合は、上限（limit）に置き換え、True を返す。
        | 下限：結果が 0 を下回る場合は、計算を破棄し、False を返す。
        | 他：そのまま計算し、True を返す。

        :param int value:
          変化量。ライフ回復や、ダメージによるライフ値の変化量。

        :return:
          Trueの時は、ライフ値の計算を制限に収まるように行った。Falseの時は、計算結果が 0 を下回るので破棄した。
        :rtype:
          bool
        """

        if 0 < self.value + value <= self.limit:
            self.value += value
            return True
        elif self.limit < self.value + value:
            self.value = self.limit
            return True
        else:
            return False


@dataclass
class LiveContext:
    """
    ノートのスコア計算のライブコンテキストのデータクラス。

    :param Life life:
        ライフ。
    :param bool on_resonance:
        センター効果・レゾナンスが有効かどうか。
    :param float base:
        ノートのスコア基礎値。
    :param int timelimit:
        最後のノートの時間（単位時間当たり）。
    :param int size:
        人数。
    :param int vocal_appeal:
        ゲストを除くユニットメンバーのボーカルアピール値
    :param int dance_appeal:
        ゲストを除くユニットメンバーのダンスアピール値
    :param int visual_appeal:
        ゲストを除くユニットメンバーのビジュアルアピール値
    :param SongType livesong_type:
        ライブの楽曲タイプ。楽曲要件の判定に用いる。
    :param set[IdolType] set_idoltypes:
        ゲストを含むユニットメンバーのアイドルタイプの集合。
    :param list[int] list_numbers_by_type:
        ゲストを含むユニットメンバーのアイドルタイプ（ドミナントアイドルタイプを含む）別の人数リスト。
            - 0: キュートアイドルタイプ、キュートドミナントアイドルタイプ、
            - 1: クールアイドルタイプ、クールドミナントアイドルタイプ、
            - 2 パッションアイドルタイプ、パッションドミナントアイドルタイプ
    :param list[IdolType] list_idoltypes:
        ゲストを除くユニットメンバーのアイドルタイプ。
    :param list[int] list_intervals:
        ゲストを除くユニットメンバーの特技の発動間隔（単位時間当たり）のリスト。
    :param list[float] list_probabilities:
        ``appeals`` で求めたゲストを除くユニットメンバーの特技の発動確率のリスト。
    :param list[int] list_durations:
        ``appeals`` で求めたゲストを除くユニットメンバーの特技の継続期間（単位時間当たり）のリスト。
    :param list[Skill] list_skills:
        ゲストを除くユニットメンバーの特技リスト。
    """

    life: Life = field(default_factory=Life)
    on_resonance: bool = False
    base: float = 0.0
    timelimit: int = 0
    size: int = 0
    vocal_appeal: int = 0
    dance_appeal: int = 0
    visual_appeal: int = 0
    livesong_type: SongType = SongType.ALL
    set_idoltypes: set[IdolType] = field(default_factory=set)
    list_numbers_by_type: list[int] = field(default_factory=list)
    list_idoltypes: list[IdolType] = field(default_factory=list)
    list_intervals: list[int] = field(default_factory=list)
    list_probabilities: list[float] = field(default_factory=list)
    list_durations: list[int] = field(default_factory=list)
    list_skills: list[Skill] = field(default_factory=list)


def wrap_skillpart_effectvalues(func: Callable) -> Callable:
    """
    特技パーツの特技効果量配列を返す関数のラッパー関数。

    :前処理: 無し。
    :後処理: デバッグログの出力。

    :param Callable func: 被ラッパー関数。

    :return: 被ラッパー関数。
    :rtype: Callable
    """

    @wraps(func)
    def wrapper(note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray) -> np.ndarray:
        """
        特技パーツの特技効果量配列を返す。

        適用メンバー（ブースト先）、適用アイコン、適用判定を調べ、効果量を返す。

        :param Note note: スコア計算対象のノート。
        :param int position: 特技を有するアイドルのライブ立ち位置。
        :param LiveContext context: ライブコンテキスト。
        :param SkillPart skillpart: 特技パーツ。
        :param np.ndarray data:
            特技パーツの特技効果量配列。

            - 0: 特技系統（スコア系、COMBO系、オルタネイト系、ミューチャル系）
            - 1: メンバー
            - 2: 効果量（ボーナス、ブースト）

        :return: 特技パーツの特技効果量配列。
        :rtype: np.ndarray
        """

        result = partial(func, note, position, context, skillpart, data)()
        LibsStageLogger.debug(f"特技パーツ・{skillpart.name}の特技効果量配列: {result}")
        return result

    return wrapper


@wrap_skillpart_effectvalues
def skillpart_bonus_score(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・スコアボーナスの特技効果量配列を返す。

    対象特技
        SCOREボーナス
            __秒毎、_確率で__間、__のスコア__%アップ
        スライドアクト、フリックアクト、ロングアクト
            __秒毎、__確率で__間、__のスコア_%アップ、__アイコンなら__%アップ
        キュートフォーカス、クールフォーカス、パッションフォーカス
            __アイドルのみ編成時、__秒毎、__確率で__間、PERFECTのスコア__%アップ、COMBOボーナス__%アップ
        コーディネート
            __秒毎、__確率で__間、__のスコア__%アップ、COMBOボーナス__%アップ
        コンセントレーション
            __秒毎、__確率で__間、__のスコア__%アップ、PERFECT判定される時間が短くなる
        オーバーロード
            __秒毎、__確率でライフを__消費し、__間__のスコア__%アップ、__でもCOMBO継続
        トリコロール・スパイク
            全タイプ楽曲で3タイプ全てのアイドル編成時、__秒毎、__確率でライフを__消費し、__間、__のスコア__%アップ、COMBOボーナス__%アップ
        トリコロール・シナジー
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、__のスコア__%アップ/ライフ__回復、COMBOボーナス__%アップ
        ボーカルモチーフ、ダンスモチーフ、ビジュアルモチーフ
            __秒毎、__確率で__間、ユニットの__アピール値が多いほどPERFECTのスコアアップ
        ミューチャル
            __秒毎、__確率で__間、スコア__%ダウン、LIVE中に発動した最も高いCOMBOボーナス効果を極大アップして適用

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・スコアボーナスの特技効果量配列。
    :rtype: np.ndarray
    """

    result: float = data[IndicesSkillCategory.SCORE][position][IndicesSkillCategoryElement.BONUS]

    match [skillpart.icon, skillpart.value]:
        case [IconType.NA, float(value)] if value >= 0.0:
            # スライドアクト、フリックアクト、ロングアクトへの上書きを回避
            result = value if value > result else result

        case [IconType.NA, float(value)] if value < 0.0:
            # ミューチャルのスコアボーナスダウン
            result = value

        case [IconType.NA, str(MOTIF)]:
            match MOTIF:
                case "ユニットのボーカルアピール値が多いほど":
                    # ボーカルモチーフ
                    result = Simulator._motives.value(appeal=context.vocal_appeal, grand=False)

                case "ユニットのダンスアピール値が多いほど":
                    # ダンスモチーフ
                    result = Simulator._motives.value(appeal=context.dance_appeal, grand=False)

                case "ユニットのビジュアルアピール値が多いほど":
                    # ビジュアルモチーフ
                    result = Simulator._motives.value(appeal=context.visual_appeal, grand=False)

                case _:
                    LibsStageLogger.error(f"特技パーツ：モチーフの効果量不明。{skillpart.value}")

        case [IconType.SLIDE, float(value)] if note.type in {
            NoteType.SLIDE_ON,
            NoteType.SLIDE_OFF,
            NoteType.SLIDE_PASS,
            NoteType.SLIDE_FLICK_LEFT,
            NoteType.SLIDE_FLICK_RIGHT,
        }:
            # スライドアクト
            result = value

        case [IconType.FLICK, float(value)] if note.type in {
            NoteType.FLICK_LEFT,
            NoteType.FLICK_RIGHT,
            NoteType.SLIDE_FLICK_RIGHT,
            NoteType.SLIDE_FLICK_LEFT,
            NoteType.LONG_FLICK_LEFT,
            NoteType.LONG_FLICK_RIGHT,
        }:
            # フリックアクト
            result = value

        case [IconType.LONG, float(value)] if note.type in {
            NoteType.LONG_ON,
            NoteType.LONG_OFF,
            NoteType.LONG_FLICK_LEFT,
            NoteType.LONG_FLICK_RIGHT,
        }:
            # ロングアクト
            result = value

        case _:
            LibsStageLogger.error(f"特技パーツ：スコアボーナスの条件不適合。{skillpart.icon}, {skillpart.value}")

    data[IndicesSkillCategory.SCORE][position][IndicesSkillCategoryElement.BONUS] = result
    return data


@wrap_skillpart_effectvalues
def skillpart_bonus_combo(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・COMBOボーナスの特技効果量配列を返す。

    対象特技
        COMBOボーナス
            __秒毎、__確率で__間、COMBOボーナス__%アップ
        ライフスパークル
            __秒毎、__確率で__間、ライフ値が多いほどCOMBOボーナスアップ
        キュートフォーカス、クールフォーカス、パッションフォーカス
            __アイドルのみ編成時、__秒毎、__確率で__間、PERFECTのスコア__%アップ、COMBOボーナス__%アップ
        コーディネート
            __秒毎、__確率で__間、__のスコア__%アップ、COMBOボーナス__%アップ
        オーバードライブ
            __秒毎、__確率で__間、COMBOボーナス__%アップ、__でライフ__回復、__のみCOMBO継続
        オールランド
            __秒毎、__確率で__間、COMBOボーナス__%アップ、__でライフ__回復
        チューニング
            __秒毎、__確率で__間、COMBOボーナス__%アップ、__をPERFECTにする
        トリコロール・スパイク
            全タイプ楽曲で3タイプ全てのアイドル編成時、__秒毎、__確率でライフを__消費し、__間、__のスコア__%アップ、COMBOボーナス__%アップ
        トリコロール・シナジー
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、__のスコア__%アップ/ライフ__回復、COMBOボーナス__%アップ
        オルタネイト
            __秒毎、__確率で__間、COMBOボーナス__%ダウン、LIVE中に発動した最も高いスコアアップ効果を極大アップして適用

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・COMBOボーナスの特技効果量配列。
    :rtype: np.ndarray
    """

    result: float = data[IndicesSkillCategory.COMBO][position][IndicesSkillCategoryElement.BONUS]

    match skillpart.value:
        case float(value):
            result = value

        case str(LIFESPARKLE) if LIFESPARKLE == "ライフ値が多いほど":
            # ライフスパークル
            # :todo: 残ライフ値
            # :todo: 特技を発動したアイドルのレア度
            result = Simulator._lifesparkles.value(life=264, rare="SSR")

        case _:
            LibsStageLogger.error(f"特技パーツ：COMBOボーナスの条件不適合。{skillpart.value}")

    data[IndicesSkillCategory.COMBO][position][IndicesSkillCategoryElement.BONUS] = result
    return data


@wrap_skillpart_effectvalues
def skillpart_boost_score(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・スコアブーストの特技効果量配列を返す。

    対象特技
        スキルブースト
            __秒毎、__確率で__間、他アイドルの特技効果を__アップ
        キュートアンサンブル、クールアンサンブル、パッションアンサンブル
            __秒毎、__確率で__間、他の__アイドルのスコアアップ/COMBOボーナス効果を__アップ
        トリコロール・シンフォニー
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、他アイドルのスコアアップ/COMBOボーナス効果を__アップ、他特技効果を__アップ
        ドミナント・ハーモニー
            __楽曲で__と__のアイドルのみ編成時、__秒毎、__確率で__間、__アイドルのスコアアップ効果と、__アイドルのCOMBOボーナス効果をそれぞれの人数に応じてアップ

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・スコアブーストの特技効果量配列。
    :rtype: np.ndarray
    """

    result: np.ndarray = data[IndicesSkillCategory.SCORE]

    match skillpart.member:
        case IdolType.UNITS:
            # スキルブースト
            # トリコロール・シンフォニー
            # スターライトアンサンブル
            for i in range(context.size):
                result[i][IndicesSkillCategoryElement.BOOST] = SkillPart.value

        case IdolType.CUTE_OF_UNITS:
            for i in range(context.size):
                if context.list_idoltypes[i] == IdolType.CUTE:
                    match skillpart.value:
                        case float(value):
                            # キュートアンサンブル
                            result[i][IndicesSkillCategoryElement.BOOST] = value

                        case str(HARMONY) if HARMONY == "キュートアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            result[i][IndicesSkillCategoryElement.BOOST] = Simulator._dominants.value(
                                number=context.list_numbers_by_type[0], type=0, guest=True
                            )

                        case _:
                            LibsStageLogger.error("skillpart_boost_score")

        case IdolType.COOL_OF_UNITS:
            for i in range(context.size):
                if context.list_idoltypes[i] == IdolType.COOL:
                    match skillpart.value:
                        case float(value):
                            # クールアンサンブル
                            result[i][IndicesSkillCategoryElement.BOOST] = value

                        case str(HARMONY) if HARMONY == "クールアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            result[i][IndicesSkillCategoryElement.BOOST] = Simulator._dominants.value(
                                number=context.list_numbers_by_type[1], type=0, guest=True
                            )

                        case _:
                            LibsStageLogger.error("skillpart_boost_score")

        case IdolType.PASSION_OF_UNITS:
            for i in range(context.size):
                if context.list_idoltypes[i] == IdolType.PASSION:
                    match skillpart.value:
                        case float(value):
                            # パッションアンサンブル
                            result[i][IndicesSkillCategoryElement.BOOST] = value

                        case str(HARMONY) if HARMONY == "パッションアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            result[i][IndicesSkillCategoryElement.BOOST] = Simulator._dominants.value(
                                number=context.list_numbers_by_type[2], type=0, guest=True
                            )

                        case _:
                            LibsStageLogger.error("skillpart_boost_score")

        case _:
            LibsStageLogger.error(f"特技パーツ：スコアブーストの条件不適合。{skillpart.icon}, {skillpart.value}")

    data[IndicesSkillCategory.SCORE] = result
    return data


@wrap_skillpart_effectvalues
def skillpart_boost_combo(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・COMBOブーストの特技効果量配列を返す。

    対象特技
        スキルブースト
            __秒毎、__確率で__間、他アイドルの特技効果を__アップ
        キュートアンサンブル、クールアンサンブル、パッションアンサンブル
            __秒毎、__確率で__間、他の__アイドルのスコアアップ/COMBOボーナス効果を__アップ
        トリコロール・シンフォニー
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、他アイドルのスコアアップ/COMBOボーナス効果を__アップ、他特技効果を__アップ
        ドミナント・ハーモニー
            __楽曲で__と__のアイドルのみ編成時、__秒毎、__確率で__間、__アイドルのスコアアップ効果と、__アイドルのCOMBOボーナス効果をそれぞれの人数に応じてアップ

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・スコアブーストの特技効果量配列。
    :rtype: np.ndarray
    """

    match skillpart.member:
        case IdolType.UNITS:
            # スキルブースト
            # トリコロール・シンフォニー
            # スターライトアンサンブル
            for i in range(context.size):
                data[IndicesSkillCategory.COMBO][i][IndicesSkillCategoryElement.BOOST] = SkillPart.value

        case IdolType.CUTE_OF_UNITS:
            for i in range(context.size):
                if context.list_idoltypes[i] == IdolType.CUTE:
                    match skillpart.value:
                        case float(value):
                            # キュートアンサンブル
                            data[IndicesSkillCategory.COMBO][i][IndicesSkillCategoryElement.BOOST] = value

                        case str(HARMONY) if HARMONY == "キュートアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            data[IndicesSkillCategory.COMBO][i][IndicesSkillCategoryElement.BOOST] = (
                                Simulator._dominants.value(number=context.list_numbers_by_type[0], type=1, guest=True)
                            )

                        case _:
                            LibsStageLogger.error("skillpart_boost_score")

        case IdolType.COOL_OF_UNITS:
            for i in range(context.size):
                if context.list_idoltypes[i] == IdolType.COOL:
                    match skillpart.value:
                        case float(value):
                            # クールアンサンブル
                            data[IndicesSkillCategory.COMBO][i][IndicesSkillCategoryElement.BOOST] = value

                        case str(HARMONY) if HARMONY == "クールアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            data[IndicesSkillCategory.COMBO][i][IndicesSkillCategoryElement.BOOST] = (
                                Simulator._dominants.value(number=context.list_numbers_by_type[1], type=1, guest=True)
                            )

                        case _:
                            LibsStageLogger.error("skillpart_boost_score")

        case IdolType.PASSION_OF_UNITS:
            for i in range(context.size):
                if context.list_idoltypes[i] == IdolType.PASSION:
                    match skillpart.value:
                        case float(value):
                            # パッションアンサンブル
                            data[IndicesSkillCategory.COMBO][i][IndicesSkillCategoryElement.BOOST] = value

                        case str(HARMONY) if HARMONY == "パッションアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            data[IndicesSkillCategory.COMBO][i][IndicesSkillCategoryElement.BOOST] = (
                                Simulator._dominants.value(number=context.list_numbers_by_type[2], type=1, guest=True)
                            )

                        case _:
                            LibsStageLogger.error("skillpart_boost_score")

        case _:
            LibsStageLogger.error(f"特技パーツ：COMBOブーストの条件不適合。{skillpart.icon}, {skillpart.value}")

    return data


@wrap_skillpart_effectvalues
def skillpart_copy_bonus_score(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・スコアボーナスコピーの特技効果量配列を返す。

    対象特技
        リフレイン
            __秒毎、__確率で__間、LIVE中に発動した最も高いスコアアップ効果/COMBOボーナス効果を適用

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・スコアボーナスコピーの特技効果量配列。
    :rtype: np.ndarray
    """

    # 発動済みのスコアボーナスの効果量を得るなら、特技系統効果量を保持すべきか？
    # しかし、発動してもノートと合致したかは不明だな
    return data


@wrap_skillpart_effectvalues
def skillpart_copy_bonus_combo(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・COMBOボーナスコピーの特技効果量配列を返す。

    対象特技
        リフレイン
            __秒毎、__確率で__間、LIVE中に発動した最も高いスコアアップ効果/COMBOボーナス効果を適用

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・COMBOボーナスコピーの特技効果量配列。
    :rtype: np.ndarray
    """

    # 発動済みのCOMBOボーナスの効果量を得るなら、特技系統効果量を保持すべきか？
    return data


@wrap_skillpart_effectvalues
def skillpart_copy_boost_score(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・スコアブーストコピーの特技効果量配列を返す。

    対象特技
        オルタネイト
            __秒毎、__確率で__間、COMBOボーナス20%ダウン、LIVE中に発動した最も高いスコアアップ効果を極大アップして適用

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・スコアブーストコピーの特技効果量配列。
    :rtype: np.ndarray
    """

    # 発動済みのCOMBOボーナスの効果量を得るなら、特技系統効果量を保持すべきか？
    return data


@wrap_skillpart_effectvalues
def skillpart_copy_boost_combo(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・COMBOブーストコピーの特技効果量配列を返す。

    対象特技
        ミューチャル
            __秒毎、__確率で__間、スコア20%ダウン、LIVE中に発動した最も高いCOMBOボーナス効果を極大アップして適用

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・COMBOブーストコピーの特技効果量配列。
    :rtype: np.ndarray
    """

    # 発動済みのCOMBOボーナスの効果量を得るなら、特技系統効果量を保持すべきか？
    return data


@wrap_skillpart_effectvalues
def skillpart_encore(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・アンコールの特技効果量配列を返す。

    対象特技
        アンコール
            __秒毎、__確率で__間、直前に発動した他アイドルの特技効果を繰り返す

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・アンコールの特技効果量配列。
    :rtype: np.ndarray
    """

    # 未実装
    return data


@wrap_skillpart_effectvalues
def skillpart_magic(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・シンデレラマジックの特技効果量配列を返す。

    対象特技
        シンデレラマジック
            12秒毎、中確率でしばらくの間、ユニット編成アイドル全員の特技効果を発動し、最も高い効果を適用

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・シンデレラマジックの特技効果量配列。
    :rtype: np.ndarray
    """

    # 未実装
    return data


@wrap_skillpart_effectvalues
def skillpart_support_perfect(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・PERFECTサポートの特技効果量配列を返す。

    対象特技
        PERFECTサポート

        チューニング

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・PERFECTサポートの特技効果量配列。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_support_combo(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・COMBOサポートの特技効果量配列を返す。

    対象特技
        COMBOサポート

        オーバーロード

        オーバードライブ

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・COMBOサポートの特技効果量配列。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_concentration(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・集中の特技効果量配列を返す。

    対象特技
        コンセントレーション

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・集中の特技効果量配列。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_boost_support_perfect(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・PERFECTサポートブーストの特技効果量配列を返す。

    対象特技
        スキルブースト
        トリコロール・シンフォニー

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・非該当の特技効果量配列。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_boost_support_combo(
    note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray
) -> np.ndarray:
    """
    特技パーツ・COMBOサポートブーストの特技効果量配列を返す。

    対象特技
        スキルブースト
        トリコロール・シンフォニー

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・非該当の特技効果量配列。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_na(note: Note, position: int, context: LiveContext, skillpart: SkillPart, data: np.ndarray) -> np.ndarray:
    """
    特技パーツ・非該当の特技効果量配列を返す。

    対象特技
        非該当

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・非該当の特技効果量配列。
    :rtype: np.ndarray
    """

    return data


def skill_effectvalue_array(
    note: Note, position: int, context: LiveContext, timetables: list[list[TimeTable]]
) -> np.ndarray:
    """
    特技系統の特技効果量配列を返す。

    - ``position`` で指定したアイドルエピソードの特技の特技効果量配列を用意する。
        - 0: 特技系統（スコア系、COMBO系、オルタネイト系、ミューチャル系の4種類）
        - 1: メンバー（通常ライブで5人、GrandLiveで15人）
        - 2: 効果量（ボーナス、ブーストの2種類）
    - 特技発動時間割で特技の発動を確認し、特技パーツ評価で特技効果量配列を埋める。
    - 特技系統の特技効果量配列を返す。

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。
    :param list[list[TimeTable]] timetables: 特技発動時間割のリスト。

    :return: 特技系統の特技効果量配列。
    :rtype: np.ndarray
    """

    skill: Skill = context.list_skills[position]
    LibsStageLogger.debug(f"特技・{skill.skill}の特技効果量配列を計算。")

    data = np.zeros((len(IndicesSkillCategory), context.size, len(IndicesSkillCategoryElement)), dtype=float)

    # 巻き込みは、timetable.start, timetable.end を加減することで実装可能。
    if any(
        [timetable.active and timetable.start <= note.timestamp <= timetable.end for timetable in timetables[position]]
    ):
        for i, skillpart in enumerate(skill.skillparts):
            if skillpart.effect.value in skillpart_effect_funcname:
                data = skillpart_effect_funcname[skillpart.effect](note, position, context, skillpart, data)

    return data


def wrap_skill_restricted(func: Callable) -> Callable:
    """
    特技の発動要件、楽曲要件、編成要件から発動可否を返す関数のラッパー関数。

    ライブ開始時の発動要件の評価指針
        - ``ライフを__消費``
            要件満たしているとし、カウンターノートを受け取った時まで評価決定を遅延する。
        - ``シンデレラマジック``、 ``アンコール、シンデレラマジックで発動不可`` （クリスタル・ヒール）
            要件を満たしている。
    カウンターノートを受け取った時の発動要件の評価指針
        - ``ライフを__消費``
            要件を満たすかどうかを残ライフ値で評価する。
    発動要件 ``アンコール、シンデレラマジックで発動不可`` （クリスタル・ヒール）は、
    特技 ``アンコール`` の特技コピー時、特技 ``シンデレラマジック`` の他アイドルの特技発動時に参照する。

    :前処理: デバッグログを出力する。
    :後処理: 無し。

    :param Callable func: 被ラッパー関数。

    :return: 被ラッパー関数
    :rtype: Callable
    """

    @wraps(func)
    def wrapper(note: Note, position: int, context: LiveContext) -> bool:
        """
        特技の適用可否を返す。

        楽曲要件、編成要件を満たす場合などは、特技パーツを適用するように **True** を返す。

        :param Note note: スコア計算対象のノート。
        :param int position: 特技を有するアイドルのライブ立ち位置。
        :param LiveContext context: ライブコンテキスト。

        :return:
          **True** であれば、特技発動とする。
          **False** であれば、特技不発とする。
        :rtype: bool
        """

        LibsStageLogger.debug(f"特技・{context.list_skills[position].skill}を処理。")

        return partial(func, note, position, context)()

    return wrapper


@wrap_skill_restricted
def skill_restricted_na(note: Note, position: int, context: LiveContext) -> bool:
    """
    特技の発動可否を評価する。

    楽曲要件、編成要件のない特技。
        SCOREボーナス
        スライドアクト、フリックアクト、ロングアクト
        ボーカルモチーフ、ビジュアルモチーフ、ダンスモチーフ
        COMBOボーナス
        ライフスパークル
        コーディネイト
        キュートアンサンブル、クールアンサンブル、パッションアンサンブル
        リフレイン
        ライフ回復
        ミューチャル
        チューニング
        ダメージガード
        スキルブースト
        コンセントレーション
        オルタネイト
        オールラウンド
        オーバーロード（ライフ消費有り）
        オーバードライブ
        アンコール
        クリスタル・ヒール（アンコール、シンデレラマジックで発動不可）
        シンデレラマジック
        非該当
        PERFECTサポート
        COMBOサポート

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。

    :return: 特技の発動の評価結果。
    :rtype: bool
    """

    return True


@wrap_skill_restricted
def skill_restricted_unit(note: Note, position: int, context: LiveContext) -> bool:
    """
    特技の発動可否を評価する。

    編成要件のある特技。
        キュートフォーカス、クールフォーカス、パッションフォーカス
            __アイドルのみ編成時、__秒毎、__確率で__間、PERFECTのスコア__%アップ、COMBOボーナス__%アップ
        トリコロール・シナジー
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、PERFECTのスコア__%アップ/ライフ__回復、COMBOボーナス__%アップ
        トリコロール・シンフォニー
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、他アイドルのスコアアップ/COMBOボーナス効果を特大アップ、他特技効果を大アップ

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。

    :return: 特技の発動の評価結果。
    :rtype: bool
    """

    skill: Skill = context.list_skills[position]
    match skill.formation:
        case UnitType.ONLY_CUTE if context.set_idoltypes == {IdolType.CUTE}:
            # キュートフォーカス
            return True

        case UnitType.ONLY_COOL if context.set_idoltypes == {IdolType.COOL}:
            # クールフォーカス
            return True

        case UnitType.ONLY_PASSION if context.set_idoltypes == {IdolType.PASSION}:
            # パッションフォーカス
            return True

        case UnitType.ALL if context.set_idoltypes == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・シナジー
            # トリコロール・シンフォニー
            return True

    return False


@wrap_skill_restricted
def skill_restricted_music(note: Note, position: int, context: LiveContext) -> bool:
    """
    特技の発動可否を評価する。

    楽曲要件のある特技。
        スターライト・アンサンブル
            全タイプ楽曲で、__秒毎、__確率で__間、他アイドルのスコアアップ/COMBOボーナス効果を極大アップ

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。

    :return: 特技の発動の評価結果。
    :rtype: bool
    """

    skill: Skill = context.list_skills[position]
    match skill.music:
        case MusicType.ALL if context.livesong_type == SongType.ALL:
            # スターライト・アンサンブル
            return True

    return False


@wrap_skill_restricted
def skill_restricted_music_and_unit(note: Note, position: int, context: LiveContext) -> bool:
    """
    特技の発動可否を評価する。

    楽曲要件と編成要件のある特技。
        トリコロール・スパイク（ライフ消費有り）
            全タイプ楽曲で3タイプ全てのアイドル編成時、__秒毎、__確率でライフを__消費し、__間、PERFECTのスコア__%アップ、COMBOボーナス__%アップ
        ドミナント・ハーモニー
            __楽曲で__と__のアイドルのみ編成時、__秒毎、__確率で__間、__アイドルのスコアアップ効果と、__アイドルのCOMBOボーナス効果をそれぞれの人数に応じてアップ

    :param Note note: スコア計算対象のノート。
    :param int position: 特技を有するアイドルのライブ立ち位置。
    :param LiveContext context: ライブコンテキスト。

    :return: 特技の発動の評価結果。
    :rtype: bool
    """

    skill: Skill = context.list_skills[position]
    match [skill.music, skill.formation]:
        case [MusicType.ALL, UnitType.ALL] if context.livesong_type == SongType.ALL and context.set_idoltypes == {
            IdolType.CUTE,
            IdolType.COOL,
            IdolType.PASSION,
        }:
            # トリコロール・スパイク
            return True

        case [MusicType.CUTE, UnitType.ONLY_COOL_AND_CUTE] if (
            context.livesong_type == SongType.CUTE and context.set_idoltypes == {IdolType.CUTE, IdolType.COOL}
        ):
            # ドミナント・ハーモニー
            return True

        case [MusicType.CUTE, UnitType.ONLY_PASSION_AND_CUTE] if (
            context.livesong_type == SongType.CUTE and context.set_idoltypes == {IdolType.CUTE, IdolType.PASSION}
        ):
            # ドミナント・ハーモニー
            return True

        case [MusicType.COOL, UnitType.ONLY_CUTE_AND_COOL] if (
            context.livesong_type == SongType.COOL and context.set_idoltypes == {IdolType.CUTE, IdolType.COOL}
        ):
            # ドミナント・ハーモニー
            return True

        case [MusicType.COOL, UnitType.ONLY_PASSION_AND_COOL] if (
            context.livesong_type == SongType.COOL and context.set_idoltypes == {IdolType.COOL, IdolType.PASSION}
        ):
            # ドミナント・ハーモニー
            return True

    return False


skillpart_effect_funcname: dict[str, Callable] = {
    "スコアボーナス": skillpart_bonus_score,
    "COMBOボーナス": skillpart_bonus_combo,
    "スコアブースト": skillpart_boost_score,
    "COMBOブースト": skillpart_boost_combo,
    "スコアボーナスコピー": skillpart_copy_bonus_score,  # リフレインの特技パーツ
    "COMBOボーナスコピー": skillpart_copy_bonus_combo,  # リフレインの特技パーツ
    "スコアブーストコピー": skillpart_copy_boost_score,  # オルタネイトのメインの特技パーツ
    "COMBOブーストコピー": skillpart_copy_boost_combo,  # ミューチャルのメインの特技パーツ
    # "ライフ回復": skillpart_recovery,
    # "ダメージガード": skillpart_no_damage,  # 他の特技のライフ消費を無効化
    # "ライフ減少量ダウン": skillpart_down_damage,  # クリスタル・ヒール、他の特技のライフ消費を減少
    # "LIVE開始時にライフ回復": skillpart_recovery_at_start,  # クリスタル・ヒール、ライブ開始時のみ発動
    "非該当": skillpart_na,  # 無処理
    "集中": skillpart_concentration,  # 無処理
    "COMBOサポート": skillpart_support_combo,  # 無処理
    "PERFECTサポート": skillpart_support_perfect,  # 無処理
    "アンコール": skillpart_encore,  # コピーした特技によって異なる
    "シンデレラマジック": skillpart_magic,  # コピーした特技によって異なる
    # "ライフ回復ブースト": skillpart_boost_recovery,
    # "ライフ回復付与": skillpart_add_recovery,
    # "ライフ減少量ダウンブースト": skillpart_boost_down_damage,
    "PERFECTサポートブースト": skillpart_boost_support_perfect,  # 無処理
    "COMBOサポートブースト": skillpart_boost_support_combo,  # 無処理
}

skill_restricted_funcname: dict[str, Callable] = {
    # skill_restricted_na
    "SCOREボーナス": skill_restricted_na,
    "スライドアクト": skill_restricted_na,
    "フリックアクト": skill_restricted_na,
    "ロングアクト": skill_restricted_na,
    "ボーカルモチーフ": skill_restricted_na,
    "ビジュアルモチーフ": skill_restricted_na,
    "ダンスモチーフ": skill_restricted_na,
    "COMBOボーナス": skill_restricted_na,
    "ライフスパークル": skill_restricted_na,
    "コーディネイト": skill_restricted_na,
    "キュートアンサンブル": skill_restricted_na,
    "クールアンサンブル": skill_restricted_na,
    "パッションアンサンブル": skill_restricted_na,
    "リフレイン": skill_restricted_na,
    "ライフ回復": skill_restricted_na,
    "ミューチャル": skill_restricted_na,
    "チューニング": skill_restricted_na,
    "ダメージガード": skill_restricted_na,
    "スキルブースト": skill_restricted_na,
    "コンセントレーション": skill_restricted_na,
    "オルタネイト": skill_restricted_na,
    "オールラウンド": skill_restricted_na,
    "オーバーロード": skill_restricted_na,
    "オーバードライブ": skill_restricted_na,
    "アンコール": skill_restricted_na,
    "クリスタル・ヒール": skill_restricted_na,
    "シンデレラマジック": skill_restricted_na,
    "非該当": skill_restricted_na,
    "PERFECTサポート": skill_restricted_na,
    "COMBOサポート": skill_restricted_na,
    # skill_restricted_unit
    "キュートフォーカス": skill_restricted_unit,
    "クールフォーカス": skill_restricted_unit,
    "パッションフォーカス": skill_restricted_unit,
    "トリコロール・シナジー": skill_restricted_unit,
    "トリコロール・シンフォニー": skill_restricted_unit,
    # skill_restricted_music
    "スターライトアンサンブル": skill_restricted_music,
    # skill_restricted_music_and_unit
    "トリコロール・スパイク": skill_restricted_music_and_unit,
    "ドミナント・ハーモニー": skill_restricted_music_and_unit,
}


class Simulator:
    """
    デレステのライブのスコア計算シミュレーター。

    :param str MusicFilename: デレステ譜面データのファイル名。
    """

    _episodes: Episodes = Episodes()
    _skills: Skills = Skills()
    _musiclevels: MusicLevels = MusicLevels()
    _comborates: ComboRates = ComboRates()
    _motives: Motives = Motives()
    _dominants: Dominants = Dominants()
    _lifesparkles: Lifesparkles = Lifesparkles()

    def __init__(self, music: Music) -> None:

        self._music: Music = music

        LibsStageLogger.info(f"{self.__class__.__name__}.init: 初期化完了。")

    @classmethod
    def load(cls) -> None:
        """
        データベースを読み込む。

        エピソード、特技、楽曲レベル、コンボ倍率、特技モチーフ効果量、特技ドミナント・ハーモニー効果量、\
            特技ライフスパークル効果量のデータベースを読み込む。
        シミュレーション実行前に行うこと。
        
        :strong:`データベースに変更があれば、再実行する。`
        """

        cls._episodes.load()
        cls._skills.load()
        cls._musiclevels.load()
        cls._comborates.load()
        cls._motives.load()
        cls._dominants.load()
        cls._lifesparkles.load()

        LibsStageLogger.info(f"{cls.__name__}.load: データベースの読み込み完了。")

    def run(self, isresonance: bool, unit: list, supports: list = []) -> list[int]:
        """
        ノートのスコア計算シミュレーションを行う。

        引数は、``アピール値計算`` の出力にそれぞれ対応している。

        :param bool isresonance:
            センター効果・レゾナンスが有効かどうか。
        :param list unit:
            ゲストを含むユニットメンバーのデータリスト。**LiveCarnival** では、ゲストを含まない。
                - 0: エピソード名
                - 1: ボーカルアピール値
                - 2: ダンスアピール値
                - 3: ビジュアルアピール値
                - 4: ライフ値
                - 5: 特技発動確率
                - 6: 特技継続期間（秒）
        :param list supports:
            サポートメンバーのデータリスト。**LiveCarnival** では、不要。
                - 0: エピソード名
                - 1: ボーカルアピール値
                - 2: ダンスアピール値
                - 3: ビジュアルアピール値
        :return: ノートのスコア計算結果リスト。
        :rtype: list[int]
        """

        def number_type(episodes: list[Episode], idoltype: IdolType, dominant: DominantType) -> int:
            """
            ゲストを含むユニットメンバーのアイドルタイプ（ドミナントアイドルタイプを含む）別の人数を数える。

            :param list[Episode] episodes: ゲストを含むユニットメンバーのエピソードリスト。
            :param IdolType idoltype: 数えたいアイドルタイプ。

            :return: ゲストを含むユニットメンバーのアイドルタイプ（ドミナントアイドルタイプを含む）別の人数。
            :rtype: int
            """

            temp = filter(lambda episode: any([episode.type == idoltype, episode.dominant == dominant]), episodes)
            return len(list(temp))

        seed()

        # ゲストを含むユニットメンバーエピソードリスト。
        episodes: list[Episode] = [Simulator._episodes.get(episode) for episode in unit[0] if isinstance(episode, str)]

        live_context = LiveContext(
            on_resonance=isresonance,
            base=self._base_score_for_note(sum(sum(s) for s in unit[1:4]) + sum(sum(s) for s in supports[1:4])),
            life=Life(value=sum([life for life in unit[4]])),
            timelimit=self._music.last_note.timestamp,
            size=UNIT_SIZE,
            vocal_appeal=sum(unit[1][:UNIT_SIZE]),
            dance_appeal=sum(unit[2][:UNIT_SIZE]),
            visual_appeal=sum(unit[3][:UNIT_SIZE]),
            livesong_type=self._music.song.type,
            set_idoltypes={episode.type for episode in episodes},
            list_numbers_by_type=[
                number_type(episodes, IdolType.CUTE, DominantType.CUTE),
                number_type(episodes, IdolType.COOL, DominantType.COOL),
                number_type(episodes, IdolType.PASSION, DominantType.PASSION),
            ],
            list_idoltypes=[episode.type for episode in episodes[:UNIT_SIZE]],
            list_intervals=[
                int(Simulator._skills.get(episode.skill).interval * FPS) for episode in episodes[:UNIT_SIZE]
            ],
            list_probabilities=unit[5][:UNIT_SIZE],
            list_durations=[int(timestamp * FPS) for timestamp in unit[6][:UNIT_SIZE]],
            list_skills=[Simulator._skills.get(episode.skill) for episode in episodes[:UNIT_SIZE]],
        )

        timetables: list[list[TimeTable]] = self._skill_timetables(live_context)

        LibsStageLogger.debug(f"楽曲: {self._music.song.type}タイプ、レベル{self._music.song.level}")
        LibsStageLogger.debug(f"特技: {[skill.skill for skill in live_context.list_skills]}")
        LibsStageLogger.debug(f"特技発動確率: {live_context.list_probabilities}")
        LibsStageLogger.debug(f"特技継続期間: {live_context.list_durations}")
        LibsStageLogger.debug(f"基礎値: {live_context.base}")
        LibsStageLogger.debug(f"初期ライフ: {live_context.life}")

        LibsStageLogger.info(f"{self.__class__.__name__}.run: シミュレーションを開始。")

        self.combo: int = 0
        return list(
            filter(
                None,
                (
                    self._streaming_note_by_note(note=note, context=live_context, timetables=timetables)
                    for note in sorted(self._music.notes(include_intervals=1))
                ),
            )
        )

    def _streaming_note_by_note(
        self, note: Note, context: LiveContext, timetables: list[list[TimeTable]]
    ) -> int | None:
        """
        **note** 単位でライブを進める。

        **NoteType** によって、以下のどちらの処理を行う。
            特技発動時にライフ消費判定のある特技発動時間割の更新（カウンターノートを1秒間隔で挿入しておく）。
            ノートのスコア計算。

        :param Note note: スコア計算対象のノート。
        :param LiveContext context: ライブコンテキスト。
        :param list[list[TimeTable]] timetables: 特技発動時間割。

        :return: ノートのスコア。
        :rtype: int
        """

        match note.type:
            case NoteType.COUNT:
                # 特技発動時間割を更新（ライフ消費などの際）。
                return None

            case _:
                # ノートのスコアを計算。

                self.combo += 1  # コンボ継続
                return self._note_score(self.combo, note, context, timetables)

    def _note_score(self, combo: int, note: Note, context: LiveContext, timetables: list[list[TimeTable]]) -> int:
        """
        ノートのスコアを計算する。

        :ノートのスコア:
          :math:`基礎値\times判定倍率\timesコンボ倍率\times特技倍率`

        :param int combo: コンボ数。
        :param Note note: スコア計算対象のノート。
        :param LiveContext context: ライブコンテキスト。
        :param list[list[TimeTable]] timetables: 特技発動時間割。

        :return: ノートのスコア。
        :rtype: int
        """

        return round(
            reduce(
                mul,  # 基礎値、判定倍率、コンボ倍率、特技倍率
                [
                    context.base,
                    self._perfection_rate("PERFECT"),
                    Simulator._comborates.rate(combo / self._music.note_number),
                    reduce(
                        mul,  # 特技系統（スコア系、COMBO系、オルタネイト系、ミューチャル系）倍率
                        self._skillcategory_rates(note=note, context=context, timetables=timetables),
                    ),
                ],
            )
        )

    def _base_score_for_note(self, appeals: int) -> float:
        """
        ノートの基礎値を計算する。

        :math:`\frac{全アピール値\times曲係数}{ノート数}`

        :param int appeals: ゲストを含むユニットメンバーのアピール（ボーカル・ダンス・ビジュアル）値合計
        :return: ノートの基礎値。
        :rtype: float
        """

        return appeals * Simulator._musiclevels.rate(self._music.song.level) / self._music.note_number

    def _perfection_rate(self, perfection: str) -> float:
        """
        ノート判定の判定倍率を返す。

        判定倍率は、ノートの判定によって決まる値のこと。
        ここでは、 ``PERFECT`` のみのフルコンボとして簡略化している。

        :param str perfection: ノート判定
        :return: 判定倍率
        :rtype: float
        """

        return 1.0

    def _skill_timetables(self, context: LiveContext) -> list[list[TimeTable]]:
        """
        ゲストを除くユニットメンバーの特技発動タイムテーブルを作成する。

        特技の発動要件・楽曲要件・編成要件を満たし、特技発動確率が乱数値以上の時に発動する。
        ただし、残ライフ値が判らないので、発動要件 **ライフを__消費** は暫定で :math:`active=True` とする。
        最後のノートの3秒前までが、特技発動の限界。

        :param LiveContext context: 特技発動時間割のコンテキスト。

        :return: 特技発動タイムテーブル。
        :rtype: list[list[TimeTable]]
        """

        timetables: list = list()

        # ユニットメンバーの特技時間割
        for position, skill in enumerate(context.list_skills):
            # 初回、特技は発動しない。
            # :todo: クリスタル・ヒールは初回に発動（発動間隔 0）するだけ。
            timetable: list = [TimeTable(active=False, start=0, end=int(context.list_durations[position]))]

            jcycle: int = 1
            while skill.interval != 0 and (context.timelimit - 3 * FPS) > context.list_intervals[position] * jcycle:
                # 特技発動間隔が 0 の場合は、次回以降の特技時間割が不要
                # 初回より後から、最後のノートの3秒前までの特技時間割を作成

                pass_song_and_unit: bool = False  # 特技の発動／不発
                if skill_restricted_funcname[skill.skill](
                    note=Note(timestamp=context.list_intervals[position] * jcycle),
                    position=position,
                    context=context,
                ):
                    pass_song_and_unit = True

                timetable.append(
                    TimeTable(
                        active=True
                        if random() < context.list_probabilities[position] and pass_song_and_unit
                        else False,
                        start=context.list_intervals[position] * jcycle,
                        end=context.list_intervals[position] * jcycle + context.list_durations[position],
                    )
                )
                jcycle += 1
            timetables.append(timetable)

        return timetables

    def _skillcategory_rates(self, note: Note, context: LiveContext, timetables: list[list[TimeTable]]) -> list[float]:
        """
        ノートの特技系統（参照：列挙クラス ``IndicesSkillCategory``）倍率を計算する。

        まず、ゲストを除くユニットメンバーそれぞれの特技系統の特技効果量を求める。
        その最大値をユニットの特技系統の特技効果量として、特技系統倍率に変換し返す。。
        ただし、センター効果・レゾナンスが有効な場合は、特技系統ごとに全メンバーの総和をユニットの特技効果量とする。

        :param Note note: ノート。
        :param SkillContext context: 特技コンテキスト。
        :param list[list[TimeTable]] timetables: ゲストを除くユニットメンバーの特技発動時間割。

        :return: 特技系統倍率リスト。
        :rtype: list[float]
        """

        # 絶対値で比較して大きい方を返すnumpy.ufunc定義
        abs_max = np.frompyfunc(lambda x, y: x if abs(x) >= abs(y) else y, 2, 1)

        # 特技のボーナス＆ブーストの効果量（小数点第2位で切り上げ）を返すnumpy.ufunc定義
        # ただし、ボーナスが負の時は、ブーストは無視。
        def bonus_boost_pyfunc(bonus: float, boost: float) -> Any:
            result: float = 0.0
            if bonus >= 0:
                result = bonus * (1.0 + boost)
            else:
                result = bonus
            return ceil(100.0 * result) / 100.0

        bonus_boost = np.frompyfunc(bonus_boost_pyfunc, 2, 1)

        effectvaluearray: np.ndarray = np.zeros(
            (context.size, len(IndicesSkillCategory), context.size, len(IndicesSkillCategoryElement))
        )
        for position, skill in enumerate(context.list_skills):
            effectvaluearray[position] = skill_effectvalue_array(
                note=note,
                position=position,
                context=context,
                timetables=timetables,
            )

        # メンバーごとに纏める。
        effectvaluearray = abs_max.reduce(effectvaluearray, axis=0)
        # ボーナス＆ブーストの効果量に変換する。
        effectvaluearray = bonus_boost.reduce(effectvaluearray, axis=2)

        # 特技系統の特技効果量を最も大きい効果量とする。
        # センター効果・レゾナンスが有効な場合は、特技系統ごとに特技効果量を全て加算する。
        effectvaluearray = (
            np.add.reduce(effectvaluearray, axis=1)
            if context.on_resonance
            else abs_max.reduce(effectvaluearray, axis=1)
        )

        LibsStageLogger.debug(f"{note.timestamp * note.time_base:.2f} 秒の特技系統効果量 - {effectvaluearray}")

        # 特技系統の特技効果量に1.0を加えて特技倍率に変換し、特技系統倍率リストとして返す。
        return (effectvaluearray + 1.0).tolist()


if __name__ == "__main__":
    print(__file__)
