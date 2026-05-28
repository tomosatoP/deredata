"""
デレステの ``スコア計算`` を扱うモジュール。

``アピール値計算モジュール`` で求めたアピール値などからスコアをシミュレートする。
まずは、通常のゲストメンバー有りの ``WIDEライブ`` に対応する。
``GrandLive`` や ``LiveCarnival（Booth効果）`` にも対応したい。

:入力:
    デレステ譜面データのファイル名。アピール値計算に用いたファイルと一致させること。
    
    アピール値計算の結果 ``isresonance``
        - レゾナンスの適否。

    アピール値計算の結果 ``unit``
        - 0: ゲストを含むユニットメンバーのエピソード名リスト。
        - 1: ゲストを含むユニットメンバーのボーカルアピール値リスト。
        - 2: ゲストを含むユニットメンバーのダンスアピール値リスト。
        - 3: ゲストを含むユニットメンバーのビジュアルアピール値リスト。
        - 4: ゲストを含むユニットメンバーのライフのリスト。
        - 5: ユニットメンバーの特技発動確率のリスト。
        - 6: ユニットメンバーの特技継続期間のリスト。
    
    アピール値計算の結果 ``supports`` （*LiveCarnivalでは、不要。*）
        - 0: サポートメンバーのエピソード名リスト。
        - 1: サポートメンバーのボーカルアピール値リスト。
        - 2: サポートメンバーのダンスアピール値リスト。
        - 3: サポートメンバーのビジュアルアピール値リスト。

:出力:
    ノートスコアのリスト

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
import re
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
from deredata.libs.database.skills import Skill, Skills, SkillPart, IconType, SkillTriggerType
from deredata.libs.database.musiclevels import MusicLevels
from deredata.libs.database.comborates import ComboRates
from deredata.libs.database.motif import Motives
from deredata.libs.database.dominant import Dominants
from deredata.libs.database.lifesparkle import Lifesparkles

from kivy.logger import Logger as LibsStageLogger

UNIT_SIZE: int = 5  # とりあえず5人固定で実装
re_excluding_digits = re.compile(r"\D")  # 数字以外に適用する正規表現


class StageError(Exception):
    """Stageモジュールのエラーハンドラ"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsStageLogger.error(f"StageError: {args}")


class SkillCategoryElementIndices(IntEnum):
    """
    特技系統の要素の列挙クラス。特技効果量リストもしくは配列の添え字に相当する。

    :param 0 BONUS: ボーナス。
    :param 1 BOOST: ブースト。
    """

    BONUS = 0
    BOOST = 1


class SkillCategoryIndices(IntEnum):
    """
    特技系統の列挙クラス。特技効果量リストもしくは配列の添え字に相当する。

    :param 0 SCORE: スコアアップ系（ミューチャル・スコアダウンも含む）。
    :param 1 COMBO: COMBOボーナス系（オルタネイト・COMBOダウンも含む）。
    :param 2 ALTERNATE: オルタネイト系。
    :param 3 MUTUAL: ミューチャル系。
    :param 4 RECOVERY: ライフ回復系。
    """

    SCORE = 0
    COMBO = 1
    ALTERNATE = 2
    MUTUAL = 3
    RECOVERY = 4


class ActiveStatus(IntEnum):
    """
    特技発動時間割の基礎情報・発動ステータスの列挙クラス。

    :param 0 NONE: 不発動（False相当）。
    :param 1 AVAILABLE: 発動待ち。
    :param 2 USED: 発動済み。
    """

    NONE = 0
    AVAILABLE = 1
    USED = 2


@dataclass
class Period:
    """
    特技発動時間割の基礎情報（コマ）のデータクラス。

    :param ActiveStatus status: 特技の発動ステータス。
    :param int start: time_base 当たりの特技発動開始時間。
    :param int end: time_base 当たりの特技発動終了時間。
    :param fraction time_base: 単位時間（1/FPS秒）。
    """

    status: ActiveStatus = ActiveStatus.NONE
    start: int = 0
    end: int = 0
    time_base: Fraction = Fraction(1, FPS)


@dataclass
class TimeTable:
    """
    特技発動時間割のデータクラス。

    :param list[Period] periodes: 特技発動時間割。
    """

    periodes: list[Period] = field(default_factory=list)


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
class LiveStatus:
    """
    ライブ進行（ノートのスコア計算）のステータスのデータクラス。

    :param Life life:
        ライフ。
    :param Skill skill:
        特技。
    :param SkillPart skillpart:
        特技パーツ。
    :param int position:
        特技を持つアイドルのライブ中の立ち位置。

        - 0: センター
        - 1: 左隣り
        - 2: 右隣り
        - 3: 左端
        - 4: 右端
    :param list[int] skill_activated:
        Live中に発動した特技の発動タイミングのリスト（ゲストを除くユニットのアイドルの立ち位置順）。

    :todo: 特技発動時間割
    """

    life: Life = field(default_factory=Life)
    skill: Skill = field(default=Skill())
    skillpart: SkillPart = field(default=SkillPart())
    position: int = 0
    skill_activated: list[int] = field(default_factory=list)


@dataclass
class LiveContext:
    """
    ライブ進行（ノートのスコア計算）のコンテキストのデータクラス。

    :param bool on_resonance:
        センター効果・レゾナンスが有効かどうか。
    :param float base:
        ノートのスコア基礎値。
    :param int timelimit:
        最後のノートの（単位時間当たりの）時間。
    :param int size:
        人数。
    :param int vocal_appeal:
        ゲストを除くユニットメンバーのボーカルアピール値。
        特技・ボーカルモチーフの効果量の評価に用いる。
    :param int dance_appeal:
        ゲストを除くユニットメンバーのダンスアピール値。
        特技・ダンスモチーフの効果量の評価に用いる。
    :param int visual_appeal:
        ゲストを除くユニットメンバーのビジュアルアピール値。
        特技・ビジュアルモチーフの効果量の評価に用いる。
    :param SongType livesong_type:
        ライブの楽曲タイプ。
        楽曲要件の判定に用いる。
    :param set[IdolType] idoltypes_set:
        ゲストを含むユニットメンバーのアイドルタイプの集合。
        編成要件の判定に用いる。
    :param list[int] type_numbers_list:
        ゲストを含むユニットメンバーのアイドルタイプ（ドミナントアイドルタイプを含む）別の人数リスト。
        特技・ドミナント・ハーモニーの効果量の評価に用いる。

        - 0: キュートアイドルタイプ、キュートドミナントアイドルタイプ、
        - 1: クールアイドルタイプ、クールドミナントアイドルタイプ、
        - 2 パッションアイドルタイプ、パッションドミナントアイドルタイプ
    :param list[IdolType] idoltypes_list:
        ゲストを除くユニットメンバーのアイドルタイプ。
        特技・アイドルタイプ・アンサンブル、ドミナント・ハーモニーの適用メンバーの評価に用いる。
    :param list[int] intervals_list:
        ゲストを除くユニットメンバーの特技の発動間隔（単位時間当たり）のリスト。
        特技発動時間割の作成、更新に用いる。
    :param list[float] probabilities_list:
        ``appeals`` で求めたゲストを除くユニットメンバーの特技の発動確率のリスト。
        特技発動時間割の作成、更新に用いる。
    :param list[int] durations_list:
        ``appeals`` で求めたゲストを除くユニットメンバーの特技の継続期間（単位時間当たり）のリスト。
        特技発動時間割の作成、更新に用いる。
    :param list[Skill] skills_list:
        ゲストを除くユニットメンバーの特技リスト。
        特技発動時間割の作成、更新に用いる。
    """

    on_resonance: bool = False
    base: float = 0.0
    timelimit: int = 0
    size: int = 0
    vocal_appeal: int = 0
    dance_appeal: int = 0
    visual_appeal: int = 0
    livesong_type: SongType = SongType.ALL
    idoltypes_set: set[IdolType] = field(default_factory=set)
    type_numbers_list: list[int] = field(default_factory=list)
    idoltypes_list: list[IdolType] = field(default_factory=list)
    intervals_list: list[int] = field(default_factory=list)
    probabilities_list: list[float] = field(default_factory=list)
    durations_list: list[int] = field(default_factory=list)
    skills_list: list[Skill] = field(default_factory=list)


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
    def wrapper(
        note: Note,
        context: LiveContext,
        status: LiveStatus,
        data: np.ndarray,
    ) -> np.ndarray:
        """
        特技パーツの特技効果量配列を返す。

        適用メンバー（ブースト先）、適用アイコン、適用判定を調べ、効果量を返す。

        :param Note note:
            スコア計算対象のノート。
        :param LiveContext context:
            ライブコンテキスト。
        :param LiveStatus status:
            ライブステータス。
        :param np.ndarray data:
            特技パーツの特技効果量配列。

            - 0: 特技系統（スコア系、COMBO系、オルタネイト系、ミューチャル系）
            - 1: メンバー
            - 2: 効果量（ボーナス、ブースト）

        :return: 特技パーツの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
        :rtype: np.ndarray
        """

        result = partial(func, note, context, status, data)()
        LibsStageLogger.debug(
            f"stage: 特技パーツ・{status.skillpart.name}の特技効果量配列 {','.join(str(result).splitlines())}"
        )
        return result

    return wrapper


@wrap_skillpart_effectvalues
def skillpart_bonus_score(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
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
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・スコアボーナスの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    score_bonus: float = data[SkillCategoryIndices.SCORE][status.position][SkillCategoryElementIndices.BONUS]

    match [status.skillpart.icon, status.skillpart.value]:
        case [IconType.NA, float(value)] if value >= 0.0:
            # スライドアクト、フリックアクト、ロングアクトへの上書きを回避
            score_bonus = value if value > score_bonus else score_bonus

        case [IconType.NA, float(value)] if value < 0.0:
            # ミューチャルのスコアボーナスダウン
            score_bonus = value

        case [IconType.NA, str(MOTIF)]:
            match MOTIF:
                case "ユニットのボーカルアピール値が多いほど":
                    # ボーカルモチーフ
                    score_bonus = Simulator._motives.value(appeal=context.vocal_appeal, grand=False)

                case "ユニットのダンスアピール値が多いほど":
                    # ダンスモチーフ
                    score_bonus = Simulator._motives.value(appeal=context.dance_appeal, grand=False)

                case "ユニットのビジュアルアピール値が多いほど":
                    # ビジュアルモチーフ
                    score_bonus = Simulator._motives.value(appeal=context.visual_appeal, grand=False)

                case _:
                    LibsStageLogger.error(f"特技パーツ：モチーフの効果量不明。{status.skillpart.value}")

        case [IconType.SLIDE, float(value)] if note.type in {
            NoteType.SLIDE_ON,
            NoteType.SLIDE_OFF,
            NoteType.SLIDE_PASS,
            NoteType.SLIDE_FLICK_LEFT,
            NoteType.SLIDE_FLICK_RIGHT,
        }:
            # スライドアクト
            score_bonus = value

        case [IconType.FLICK, float(value)] if note.type in {
            NoteType.FLICK_LEFT,
            NoteType.FLICK_RIGHT,
            NoteType.SLIDE_FLICK_RIGHT,
            NoteType.SLIDE_FLICK_LEFT,
            NoteType.LONG_FLICK_LEFT,
            NoteType.LONG_FLICK_RIGHT,
        }:
            # フリックアクト
            score_bonus = value

        case [IconType.LONG, float(value)] if note.type in {
            NoteType.LONG_ON,
            NoteType.LONG_OFF,
            NoteType.LONG_FLICK_LEFT,
            NoteType.LONG_FLICK_RIGHT,
        }:
            # ロングアクト
            score_bonus = value

        case _:
            LibsStageLogger.error(
                f"特技パーツ：スコアボーナスの条件不適合。{status.skillpart.icon}, {status.skillpart.value}"
            )

    data[SkillCategoryIndices.SCORE][status.position][SkillCategoryElementIndices.BONUS] = score_bonus
    return data


@wrap_skillpart_effectvalues
def skillpart_bonus_combo(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
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
            全タイプ楽曲で3タイプ全てのアイドル編成時、__秒毎、__確率でライフを__消費し、\
                __間、__のスコア__%アップ、COMBOボーナス__%アップ
        トリコロール・シナジー
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、__のスコア__%アップ/ライフ__回復、COMBOボーナス__%アップ
        オルタネイト
            __秒毎、__確率で__間、COMBOボーナス__%ダウン、LIVE中に発動した最も高いスコアアップ効果を極大アップして適用

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・COMBOボーナスの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    combo_bonus: float = data[SkillCategoryIndices.COMBO][status.position][SkillCategoryElementIndices.BONUS]

    match status.skillpart.value:
        case float(value):
            combo_bonus = value

        case str(LIFESPARKLE) if LIFESPARKLE == "ライフ値が多いほど":
            # ライフスパークル
            # :todo: 残ライフ値
            # :todo: 特技を発動したアイドルのレア度
            combo_bonus = Simulator._lifesparkles.value(life=status.life.value, rare="SSR")

        case _:
            LibsStageLogger.error(f"特技パーツ：COMBOボーナスの条件不適合。{status.skillpart.value}")

    data[SkillCategoryIndices.COMBO][status.position][SkillCategoryElementIndices.BONUS] = combo_bonus
    return data


@wrap_skillpart_effectvalues
def skillpart_boost_score(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・スコアブーストの特技効果量配列を返す。

    対象特技（GrandLiveでは、他のユニットのスコアボーナスもブースト対象）
        スキルブースト
            __秒毎、__確率で__間、他アイドルの特技効果を__アップ
        キュートアンサンブル、クールアンサンブル、パッションアンサンブル
            __秒毎、__確率で__間、他の__アイドルのスコアアップ/COMBOボーナス効果を__アップ
        スターライトアンサンブル
            全タイプ楽曲で、__秒毎、__確率で__間、他アイドルのスコアアップ/COMBOボーナス効果を極大アップ
        トリコロール・シンフォニー
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、\
                他アイドルのスコアアップ/COMBOボーナス効果を__アップ、他特技効果を__アップ
        ドミナント・ハーモニー
            __楽曲で__と__のアイドルのみ編成時、__秒毎、__確率で__間、__アイドルのスコアアップ効果と、\
                __アイドルのCOMBOボーナス効果をそれぞれの人数に応じてアップ

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・スコアブーストの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    result: np.ndarray = data[SkillCategoryIndices.SCORE]
    elem: int = SkillCategoryElementIndices.BOOST

    match status.skillpart.member:
        case IdolType.UNITS:
            # スキルブースト
            # トリコロール・シンフォニー
            # スターライトアンサンブル
            for i in range(context.size):
                result[i][elem] = status.skillpart.value

        case IdolType.CUTE_OF_UNITS:
            for i in range(context.size):
                if context.idoltypes_list[i] == IdolType.CUTE:
                    match status.skillpart.value:
                        case float(value):
                            # キュートアンサンブル
                            result[i][elem] = value

                        case str(HARMONY) if HARMONY == "キュートアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            result[i][elem] = Simulator._dominants.value(
                                number=context.type_numbers_list[0], type=0, guest=True
                            )

                        case _:
                            LibsStageLogger.error(f"stage.skillpart_boost_score: {status.skillpart.name} 不明。")

        case IdolType.COOL_OF_UNITS:
            for i in range(context.size):
                if context.idoltypes_list[i] == IdolType.COOL:
                    match status.skillpart.value:
                        case float(value):
                            # クールアンサンブル
                            result[i][elem] = value

                        case str(HARMONY) if HARMONY == "クールアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            result[i][elem] = Simulator._dominants.value(
                                number=context.type_numbers_list[1], type=0, guest=True
                            )

                        case _:
                            LibsStageLogger.error(f"stage.skillpart_boost_score: {status.skillpart.name} 不明。")

        case IdolType.PASSION_OF_UNITS:
            for i in range(context.size):
                if context.idoltypes_list[i] == IdolType.PASSION:
                    match status.skillpart.value:
                        case float(value):
                            # パッションアンサンブル
                            result[i][elem] = value

                        case str(HARMONY) if HARMONY == "パッションアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            result[i][elem] = Simulator._dominants.value(
                                number=context.type_numbers_list[2], type=0, guest=True
                            )

                        case _:
                            LibsStageLogger.error(f"stage.skillpart_boost_score: {status.skillpart.name} 不明。")

        case _:
            LibsStageLogger.error(
                f"特技パーツ：スコアブーストの条件不適合。{status.skillpart.icon}, {status.skillpart.value}"
            )

    data[SkillCategoryIndices.SCORE] = result
    return data


@wrap_skillpart_effectvalues
def skillpart_boost_combo(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・COMBOブーストの特技効果量配列を返す。

    対象特技（GrandLiveでは、他のユニットのCOMBOボーナスもブースト対象）
        スキルブースト
            __秒毎、__確率で__間、他アイドルの特技効果を__アップ
        キュートアンサンブル、クールアンサンブル、パッションアンサンブル
            __秒毎、__確率で__間、他の__アイドルのスコアアップ/COMBOボーナス効果を__アップ
        スターライトアンサンブル
            全タイプ楽曲で、__秒毎、__確率で__間、他アイドルのスコアアップ/COMBOボーナス効果を極大アップ
        トリコロール・シンフォニー
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、\
                他アイドルのスコアアップ/COMBOボーナス効果を__アップ、他特技効果を__アップ
        ドミナント・ハーモニー
            __楽曲で__と__のアイドルのみ編成時、__秒毎、__確率で__間、__アイドルのスコアアップ効果と、\
                __アイドルのCOMBOボーナス効果をそれぞれの人数に応じてアップ

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・スコアブーストの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    result: np.ndarray = data[SkillCategoryIndices.COMBO]
    elem: int = SkillCategoryElementIndices.BOOST

    match status.skillpart.member:
        case IdolType.UNITS:
            # スキルブースト
            # トリコロール・シンフォニー
            # スターライトアンサンブル
            for i in range(context.size):
                result[i][elem] = status.skillpart.value

        case IdolType.CUTE_OF_UNITS:
            for i in range(context.size):
                if context.idoltypes_list[i] == IdolType.CUTE:
                    match status.skillpart.value:
                        case float(value):
                            # キュートアンサンブル
                            result[i][elem] = value

                        case str(HARMONY) if HARMONY == "キュートアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            result[i][elem] = Simulator._dominants.value(
                                number=context.type_numbers_list[0], type=1, guest=True
                            )

                        case _:
                            LibsStageLogger.error(f"stage.skillpart_boost_score: {status.skillpart.name} 不明。")

        case IdolType.COOL_OF_UNITS:
            for i in range(context.size):
                if context.idoltypes_list[i] == IdolType.COOL:
                    match status.skillpart.value:
                        case float(value):
                            # クールアンサンブル
                            result[i][elem] = value

                        case str(HARMONY) if HARMONY == "クールアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            result[i][elem] = Simulator._dominants.value(
                                number=context.type_numbers_list[1], type=1, guest=True
                            )

                        case _:
                            LibsStageLogger.error(f"stage.skillpart_boost_score: {status.skillpart.name} 不明。")

        case IdolType.PASSION_OF_UNITS:
            for i in range(context.size):
                if context.idoltypes_list[i] == IdolType.PASSION:
                    match status.skillpart.value:
                        case float(value):
                            # パッションアンサンブル
                            result[i][elem] = value

                        case str(HARMONY) if HARMONY == "パッションアイドルの人数に応じて":
                            # ドミナント・ハーモニー
                            result[i][elem] = Simulator._dominants.value(
                                number=context.type_numbers_list[2], type=1, guest=True
                            )

                        case _:
                            LibsStageLogger.error(f"stage.skillpart_boost_score: {status.skillpart.name} 不明。")

        case _:
            LibsStageLogger.error(
                f"特技パーツ：COMBOブーストの条件不適合。{status.skillpart.icon}, {status.skillpart.value}"
            )

    data[SkillCategoryIndices.COMBO] = result
    return data


@wrap_skillpart_effectvalues
def skillpart_copy_bonus_score(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・スコアボーナスコピーの特技効果量配列を返す。

    対象特技
        リフレイン
            __秒毎、__確率で__間、LIVE中に発動した最も高いスコアアップ効果/COMBOボーナス効果を適用

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・スコアボーナスコピーの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    LibsStageLogger.error("skillpart_copy_bonus_score: 実装中。")
    return data


@wrap_skillpart_effectvalues
def skillpart_copy_bonus_combo(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・COMBOボーナスコピーの特技効果量配列を返す。

    対象特技
        リフレイン
            __秒毎、__確率で__間、LIVE中に発動した最も高いスコアアップ効果/COMBOボーナス効果を適用

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・COMBOボーナスコピーの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    LibsStageLogger.error("skillpart_copy_bonus_combo: 実装中。")
    return data


@wrap_skillpart_effectvalues
def skillpart_copy_boost_score(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・スコアブーストコピーの特技効果量配列を返す。

    対象特技
        オルタネイト
            __秒毎、__確率で__間、COMBOボーナス20%ダウン、LIVE中に発動した最も高いスコアアップ効果を極大アップして適用

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・スコアブーストコピーの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    LibsStageLogger.error("skillpart_copy_boost_score: 実装中。")
    return data


@wrap_skillpart_effectvalues
def skillpart_copy_boost_combo(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・COMBOブーストコピーの特技効果量配列を返す。

    対象特技
        ミューチャル
            __秒毎、__確率で__間、スコア20%ダウン、LIVE中に発動した最も高いCOMBOボーナス効果を極大アップして適用

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・COMBOブーストコピーの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    LibsStageLogger.error("skillpart_copy_boost_combo: 実装中。")
    return data


@wrap_skillpart_effectvalues
def skillpart_encore(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・アンコールの特技効果量配列を返す。

    対象特技（GrandLiveでは、他のユニットの特技もコピー対象）
        アンコール
            __秒毎、__確率で__間、直前に発動した他アイドルの特技効果を繰り返す
            ただし、クリスタル・ヒールは、コピーしない。

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・アンコールの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    LibsStageLogger.error("skillpart_encore: 実装中。")
    return data


@wrap_skillpart_effectvalues
def skillpart_magic(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・シンデレラマジックの特技効果量配列を返す。

    対象特技
        シンデレラマジック
            12秒毎、中確率でしばらくの間、ユニット編成アイドル全員の特技効果を発動し、最も高い効果を適用
            ただし、クリスタル・ヒールは、発動しない。

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・シンデレラマジックの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    LibsStageLogger.error("skillpart_magic: 実装中。")
    return data


@wrap_skillpart_effectvalues
def skillpart_recovery(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・ライフ回復の特技効果量配列を返す。

    対象特技
        ライフ回復。
            __秒毎、__確率で__間、__でライフ__回復
        トリコロール・シナジー。
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、__のスコア__%アップ/ライフ__回復、COMBOボーナス__%アップ
        オールラウンド。
            __秒毎、__確率で__間、COMBOボーナス__%アップ、__でライフ__回復
        オーバードライブ。
            __秒毎、__確率で__間、COMBOボーナス__%アップ、__でライフ__回復、PERFECTのみCOMBO継続

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・PERFECTサポートの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    data[SkillCategoryIndices.RECOVERY][status.position][SkillCategoryElementIndices.BONUS] = status.skillpart.value

    return data


@wrap_skillpart_effectvalues
def skillpart_no_damage(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・ダメージガードの特技効果量配列を返す。

    対象特技
        ダメージガード
            __秒毎、__確率で__間、ライフが減少しなくなる

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・PERFECTサポートの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    # :todo: 特技発動要件のライフ消費
    # :todo: ブーストでライフ回付付与
    LibsStageLogger.error("skillpart_no_damage: 実装中。")
    return data


@wrap_skillpart_effectvalues
def skillpart_boost_recovery(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・ライフ回復ブーストの特技効果量配列を返す。

    対象特技
        スキルブースト。
            __秒毎、__確率で__間、他アイドルの特技効果を__アップ
        トリコロール・シンフォニー。
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、他アイドルのスコアアップ/COMBOボーナス効果を特大アップ、他特技効果を大アップ

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・PERFECTサポートの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    # :todo: ライフ回復の配列（ボーナス、ブースト）
    LibsStageLogger.error("skillpart_boost_recovery: 実装中。")
    return data


@wrap_skillpart_effectvalues
def skillpart_add_recovery(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・ライフ回復付与の特技効果量配列を返す。

    対象特技
        スキルブースト。
            __秒毎、__確率で__間、他アイドルの特技効果を__アップ
        トリコロール・シンフォニー。
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、他アイドルのスコアアップ/COMBOボーナス効果を特大アップ、他特技効果を大アップ

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・PERFECTサポートの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    # :todo: ライフ回復の配列（ボーナス、ブースト）
    # :todo: ダメージガードの発動を確認する方法を決める。
    LibsStageLogger.error("skillpart_add_recovery: 実装中。")
    return data


@wrap_skillpart_effectvalues
def skillpart_support_perfect(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・PERFECTサポートの特技効果量配列を返す。

    対象特技
        PERFECTサポート
            __秒毎、__確率で__間、__をPERFECTにする
        チューニング
            __秒毎、__確率で__間、COMBOボーナス__%アップ、__をPERFECTにする

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・PERFECTサポートの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_support_combo(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・COMBOサポートの特技効果量配列を返す。

    対象特技
        COMBOサポート
            __秒毎、__確率で__間、__でもCOMBOが継続する
        オーバーロード
            __秒毎、___確率でライフを__消費し、__間__のスコア__%アップ、__でもCOMBO継続
        オーバードライブ
            __秒毎、__確率で__間、COMBOボーナス__%アップ、PERFECTでライフ__回復、PERFECTのみCOMBO継続

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・COMBOサポートの特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_concentration(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・集中の特技効果量配列を返す。

    対象特技
        コンセントレーション
            __秒毎、__確率で__間、PERFECTのスコア__%アップ、PERFECT判定される時間が短くなる

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・集中の特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_boost_support_perfect(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・PERFECTサポートブーストの特技効果量配列を返す。

    対象特技
        スキルブースト
            __秒毎、__確率で__間、他アイドルの特技効果を大アップ
        トリコロール・シンフォニー
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、他アイドルのスコアアップ/COMBOボーナス効果を特大アップ、他特技効果を大アップ

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・非該当の特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_boost_support_combo(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・COMBOサポートブーストの特技効果量配列を返す。

    対象特技
        スキルブースト
            __秒毎、__確率で__間、他アイドルの特技効果を大アップ
        トリコロール・シンフォニー
            3タイプ全てのアイドル編成時、__秒毎、__確率で__間、他アイドルのスコアアップ/COMBOボーナス効果を特大アップ、他特技効果を大アップ

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・非該当の特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_na(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    data: np.ndarray,
) -> np.ndarray:
    """
    特技パーツ・非該当の特技効果量配列を返す。

    対象特技
        非該当

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・非該当の特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    return data


def skillcategory_menber_bonusboost_effectvalues(
    note: Note,
    context: LiveContext,
    status: LiveStatus,
    timetables: list[TimeTable],
) -> np.ndarray:
    """
    特技系統の特技効果量配列（次元：特技系統、メンバー、ボーナス＆ブースト）を返す。

    - 効果量を要素とする配列を用意する。
        - 0: 特技（通常ライブで5人分、GrandLiveで15人分）。
        - 1: 特技系統（スコア系、COMBO系、オルタネイト系、ミューチャル系の4種類）。
        - 2: メンバー（通常ライブで5人、GrandLiveで15人）。ブースト対象の指定用。
        - 3: 効果タイプ（ボーナス、ブーストの2種類）。
    - 特技発動時間割で特技の発動を確認し、特技パーツ評価で特技効果量配列を埋める。
    - **特技** で最大値を取って、特技系統の特技効果量配列に縮めて返す。

    :param Note note: スコア計算対象のノート。
    :param LiveContext context: ライブコンテキスト。
    :param LiveStatus status: ライブステータス。
    :param list[TimeTable] timetables: 特技発動時間割のリスト。

    :return: 特技系統の特技効果量配列（特技系統、メンバー、ボーナス＆ブースト）。
    :rtype: np.ndarray
    """

    # 絶対値で比較して大きい方を返すnumpy.ufunc定義
    abs_max = np.frompyfunc(lambda x, y: x if abs(x) >= abs(y) else y, 2, 1)

    data = np.zeros(
        (
            context.size,  # 特技
            len(SkillCategoryIndices),  # 特技系統
            context.size,  # メンバー
            len(SkillCategoryElementIndices),  # 効果タイプ（ボーナス、ブースト）
        ),
        dtype=float,
    )

    for position, skill in enumerate(context.skills_list):
        status.position = position
        status.skill = skill

        # 巻き込みは、period.start, period.end を加減することで実装可能。
        if any(
            [
                period.status and period.start <= note.timestamp <= period.end
                for period in timetables[status.position].periodes
            ]
        ):
            LibsStageLogger.debug(
                f"stage.skillcategory_menber_bonusboost_effectvalues: 特技・{status.skill.skill}を処理。"
            )

            for i, skillpart in enumerate(status.skill.skillparts):
                status.skillpart = skillpart
                if skillpart.effect.value in skillpart_effect_funcname:
                    data[position] = skillpart_effect_funcname[skillpart.effect](note, context, status, data[position])
                else:
                    LibsStageLogger.error(f"stage.skill_effectvalue_array: {skillpart.name} は、未実装です。")

        status.skillpart = SkillPart()
    status.position = 0
    status.skill = Skill()

    return abs_max.reduce(data, axis=0)


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

        LibsStageLogger.debug(f"stage.wrap_skill_restricted: 特技・{context.skills_list[position].skill}を処理。")

        return partial(func, note, position, context)()

    return wrapper


@wrap_skill_restricted
def skill_restricted_na(
    note: Note,
    position: int,
    context: LiveContext,
) -> bool:
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
def skill_restricted_unit(
    note: Note,
    position: int,
    context: LiveContext,
) -> bool:
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

    skill: Skill = context.skills_list[position]
    match skill.formation:
        case UnitType.ONLY_CUTE if context.idoltypes_set == {IdolType.CUTE}:
            # キュートフォーカス
            return True

        case UnitType.ONLY_COOL if context.idoltypes_set == {IdolType.COOL}:
            # クールフォーカス
            return True

        case UnitType.ONLY_PASSION if context.idoltypes_set == {IdolType.PASSION}:
            # パッションフォーカス
            return True

        case UnitType.ALL if context.idoltypes_set == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・シナジー
            # トリコロール・シンフォニー
            return True

    return False


@wrap_skill_restricted
def skill_restricted_music(
    note: Note,
    position: int,
    context: LiveContext,
) -> bool:
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

    skill: Skill = context.skills_list[position]
    match skill.music:
        case MusicType.ALL if context.livesong_type == SongType.ALL:
            # スターライト・アンサンブル
            return True

    return False


@wrap_skill_restricted
def skill_restricted_music_and_unit(
    note: Note,
    position: int,
    context: LiveContext,
) -> bool:
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

    skill: Skill = context.skills_list[position]
    match [skill.music, skill.formation]:
        case [MusicType.ALL, UnitType.ALL] if context.livesong_type == SongType.ALL and context.idoltypes_set == {
            IdolType.CUTE,
            IdolType.COOL,
            IdolType.PASSION,
        }:
            # トリコロール・スパイク
            return True

        case [MusicType.CUTE, UnitType.ONLY_COOL_AND_CUTE] if (
            context.livesong_type == SongType.CUTE and context.idoltypes_set == {IdolType.CUTE, IdolType.COOL}
        ):
            # ドミナント・ハーモニー
            return True

        case [MusicType.CUTE, UnitType.ONLY_PASSION_AND_CUTE] if (
            context.livesong_type == SongType.CUTE and context.idoltypes_set == {IdolType.CUTE, IdolType.PASSION}
        ):
            # ドミナント・ハーモニー
            return True

        case [MusicType.COOL, UnitType.ONLY_CUTE_AND_COOL] if (
            context.livesong_type == SongType.COOL and context.idoltypes_set == {IdolType.CUTE, IdolType.COOL}
        ):
            # ドミナント・ハーモニー
            return True

        case [MusicType.COOL, UnitType.ONLY_PASSION_AND_COOL] if (
            context.livesong_type == SongType.COOL and context.idoltypes_set == {IdolType.COOL, IdolType.PASSION}
        ):
            # ドミナント・ハーモニー
            return True

    return False


skillpart_effect_funcname: dict[str, Callable] = {
    "スコアボーナス": skillpart_bonus_score,  # オルタネイトのマイナス効果を含む
    "COMBOボーナス": skillpart_bonus_combo,  # ミューチャルのマイナス効果を含む
    "スコアブースト": skillpart_boost_score,
    "COMBOブースト": skillpart_boost_combo,
    "スコアボーナスコピー": skillpart_copy_bonus_score,  # リフレインの特技パーツ
    "COMBOボーナスコピー": skillpart_copy_bonus_combo,  # リフレインの特技パーツ
    "スコアブーストコピー": skillpart_copy_boost_score,  # オルタネイトの特技パーツ
    "COMBOブーストコピー": skillpart_copy_boost_combo,  # ミューチャルの特技パーツ
    "ライフ回復": skillpart_recovery,
    "ダメージガード": skillpart_no_damage,  # [特技発動要件のライフ消費] を無効化
    "アンコール": skillpart_encore,  # コピーした特技によって異なる
    "シンデレラマジック": skillpart_magic,  # コピーした特技によって異なる
    "ライフ回復ブースト": skillpart_boost_recovery,
    "ライフ回復付与": skillpart_add_recovery,  # ダメージガードをブーストし、ライフ回復
    # "ライフ減少量ダウン": skillpart_down_damage,  # クリスタル・ヒール、他の特技のライフ消費を減少
    # "LIVE開始時にライフ回復": skillpart_recovery_at_start,  # クリスタル・ヒール、ライブ開始時のみ発動
    # "ライフ減少量ダウンブースト": skillpart_boost_down_damage,  # [特技発動要件のライフ消費] を軽減
    "非該当": skillpart_na,  # 無処理
    "集中": skillpart_concentration,  # 無処理
    "COMBOサポート": skillpart_support_combo,  # 無処理
    "PERFECTサポート": skillpart_support_perfect,  # 無処理
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
            timelimit=self._music.last_note.timestamp,
            size=UNIT_SIZE,
            vocal_appeal=sum(unit[1][:UNIT_SIZE]),
            dance_appeal=sum(unit[2][:UNIT_SIZE]),
            visual_appeal=sum(unit[3][:UNIT_SIZE]),
            livesong_type=self._music.song.type,
            idoltypes_set={episode.type for episode in episodes},
            type_numbers_list=[
                number_type(episodes, IdolType.CUTE, DominantType.CUTE),
                number_type(episodes, IdolType.COOL, DominantType.COOL),
                number_type(episodes, IdolType.PASSION, DominantType.PASSION),
            ],
            idoltypes_list=[episode.type for episode in episodes[:UNIT_SIZE]],
            intervals_list=[
                int(Simulator._skills.get(episode.skill).interval * FPS) for episode in episodes[:UNIT_SIZE]
            ],
            probabilities_list=unit[5][:UNIT_SIZE],
            durations_list=[int(timestamp * FPS) for timestamp in unit[6][:UNIT_SIZE]],
            skills_list=[Simulator._skills.get(episode.skill) for episode in episodes[:UNIT_SIZE]],
        )

        timetables: list[TimeTable] = self._skill_timetables(live_context)

        live_status = LiveStatus(
            life=Life(value=sum([life for life in unit[4]])), skill_activated=[0 for _ in range(UNIT_SIZE)]
        )

        debug_massage = f"{self.__class__.__name__}.run: "

        LibsStageLogger.debug(f"{debug_massage}楽曲 - {self._music.song.type}タイプ、レベル{self._music.song.level}")
        LibsStageLogger.debug(f"{debug_massage}特技 - {[skill.skill for skill in live_context.skills_list]}")
        LibsStageLogger.debug(f"{debug_massage}特技発動確率 - {live_context.probabilities_list}")
        LibsStageLogger.debug(f"{debug_massage}特技継続期間 - {live_context.durations_list}")
        LibsStageLogger.debug(f"{debug_massage}基礎値 - {live_context.base:.2f}")
        LibsStageLogger.debug(f"{debug_massage}初期ライフ - {live_status.life}")

        LibsStageLogger.info(f"{debug_massage}シミュレーションを開始。")

        self.combo: int = 0
        return list(
            filter(
                None,
                (
                    self._streaming_note_by_note(
                        note=note,
                        context=live_context,
                        status=live_status,
                        timetables=timetables,
                    )
                    for note in sorted(self._music.notes(include_intervals=1))
                ),
            )
        )

    def _streaming_note_by_note(
        self,
        note: Note,
        context: LiveContext,
        status: LiveStatus,
        timetables: list[TimeTable],
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
                self._substract_life_upon(note, context, status, timetables)
                return None

            case _:
                # ノートのスコアを計算。

                self.combo += 1  # コンボ継続
                return self._note_score(self.combo, note, context, status, timetables)

    def _note_score(
        self,
        combo: int,
        note: Note,
        context: LiveContext,
        status: LiveStatus,
        timetables: list[TimeTable],
    ) -> int:
        """
        ノートのスコアを計算する。

        :ノートのスコア:
            :math:`基礎値\\times判定倍率\\timesコンボ倍率\\times特技倍率`

        :param int combo: コンボ数。
        :param Note note: スコア計算対象のノート。
        :param LiveContext context: ライブコンテキスト。
        :param list[TimeTable] timetables: 特技発動時間割。

        :return: ノートのスコア。
        :rtype: int
        """

        return round(
            reduce(  # 基礎値 * 判定倍率 * コンボ倍率 * 特技倍率
                mul,
                [
                    context.base,
                    self._perfection_rate("PERFECT"),
                    Simulator._comborates.rate(combo / self._music.note_number),
                    reduce(  # スコア系倍率 * COMBO系倍率 * オルタネイト系倍率 * ミューチャル系倍率
                        mul,
                        self._skillcategory_rates(
                            note=note,
                            context=context,
                            status=status,
                            timetables=timetables,
                        ),
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

    def _skill_timetables(self, context: LiveContext) -> list[TimeTable]:
        """
        ゲストを除くユニットメンバーの特技発動タイムテーブルを作成する。

        特技の発動要件・楽曲要件・編成要件を満たし、特技発動確率が乱数値以上の時に発動する。
        ただし、残ライフ値が判らないので、発動要件 **ライフを__消費** の特技を暫定で ``ActiveStatus.AVAILABLE`` とする。
        最後のノートの3秒前までが、特技発動の限界。

        :param LiveContext context: 特技発動時間割のコンテキスト。

        :return: 特技発動タイムテーブル。
        :rtype: list[TimeTable]
        """

        timetables: list = list()

        # ユニットメンバーの特技時間割
        for position, skill in enumerate(context.skills_list):
            # 初回、特技は発動しない。
            # :todo: クリスタル・ヒールの特技は、初回だけ発動（発動間隔 0）。
            timetable: TimeTable = TimeTable()
            timetable.periodes.append(
                Period(
                    start=0,
                    end=int(context.durations_list[position]),
                )
            )

            jcycle: int = 1
            while skill.interval != 0 and (context.timelimit - 3 * FPS) > context.intervals_list[position] * jcycle:
                # 特技発動間隔が 0 の場合（クリスタル・ヒールの特技）は、次回以降の特技時間割が不要。
                # 初回より後から、最後のノートの3秒前までの特技時間割を作成。

                # True: 楽曲要件と編成要件を満たしてる。
                pass_song_and_unit: bool = skill_restricted_funcname[skill.skill](
                    note=Note(timestamp=context.intervals_list[position] * jcycle),
                    position=position,
                    context=context,
                )

                # True: 特技発動確率が乱数を超えている。
                # 特技発動時間割のコマを作成。
                timetable.periodes.append(
                    Period(
                        status=ActiveStatus.AVAILABLE
                        if context.probabilities_list[position] > random() and pass_song_and_unit
                        else ActiveStatus.NONE,
                        start=context.intervals_list[position] * jcycle,
                        end=context.intervals_list[position] * jcycle + context.durations_list[position],
                    )
                )
                jcycle += 1
            timetables.append(timetable)

        return timetables

    def _substract_life_upon(
        self,
        note: Note,
        context: LiveContext,
        status: LiveStatus,
        timetables: list[TimeTable],
    ) -> None:
        """
        毎秒（カウンターノートを受け取った）、発動ステータス ``ActiveStatus.AVAILABLE`` の特技発動を確認する。

        発動ステータス ``ActiveStatus.AVAILABLE`` の特技のみ処理し、以外はスルー。
        発動時にライフ消費を必要とする特技は、残ライフ量で発動ステータスを ``USED`` ／ ``NONE`` を仕分ける。
        これ以外の特技は、発動ステータスを ``USED`` にする。
        シンデレラマジックの発動時、他のアイドルの特技を発動（コマを挿入）させる。

        :param Note note: カウンターノート。
        :param LiveContext context: ライブコンテキスト。
        :param LiveStatus status: ライブステータス。
        :param list[TimeTable] timetables: 特技発動時間割。

        :todo: 特技・ダメージガードの発動時は、ライフ消費無しで発動確定。
        :todo: 特技パーツ・ライフ消費量ダウン（特技・クリスタル・ヒール）の発動時は、減少したライフ消費量で評価する。
        """

        # まず、発動要件・アンコールを評価。直前の発動が同時発動で上書きされるのを避けるため。
        for poistion, timetable in enumerate(timetables):
            match context.skills_list[poistion].trigger:
                case SkillTriggerType.ENCORE:
                    for period in timetable.periodes:
                        if period.start == note.timestamp and period.status == ActiveStatus.AVAILABLE:
                            before_useds: list[int] = [
                                i
                                for i, timestamp in enumerate(status.skill_activated)
                                if timestamp == max(status.skill_activated)
                            ]
                            LibsStageLogger.debug(f"{self.__class__.__name__}.: {before_useds}")
                            period.status = ActiveStatus.USED
                            status.skill_activated[poistion] = note.timestamp

                case _:
                    pass

        # アンコール以外の発動要件を評価。
        for position, timetable in enumerate(timetables):
            match context.skills_list[position].trigger:
                case SkillTriggerType.ENCORE:
                    # 評価済み
                    pass

                case (
                    SkillTriggerType.SUBSTRACTLIFE_06
                    | SkillTriggerType.SUBSTRACTLIFE_09
                    | SkillTriggerType.SUBSTRACTLIFE_11
                    | SkillTriggerType.SUBSTRACTLIFE_15
                    | SkillTriggerType.SUBSTRACTLIFE_18
                    | SkillTriggerType.SUBSTRACTLIFE_25
                    | SkillTriggerType.SUBSTRACTLIFE_28
                ):
                    for period in timetable.periodes:
                        if period.start == note.timestamp and period.status == ActiveStatus.AVAILABLE:
                            value = int(re_excluding_digits.sub("", context.skills_list[position].trigger.value))
                            if status.life.update(-value):
                                period.status = ActiveStatus.USED
                                status.skill_activated[position] = note.timestamp
                            else:
                                period.status = ActiveStatus.NONE

                case SkillTriggerType.REFRAIN:
                    for period in timetable.periodes:
                        if period.start == note.timestamp and period.status == ActiveStatus.AVAILABLE:
                            period.status = ActiveStatus.USED
                            status.skill_activated[position] = note.timestamp

                case SkillTriggerType.ALTERNATE:
                    for period in timetable.periodes:
                        if period.start == note.timestamp and period.status == ActiveStatus.AVAILABLE:
                            period.status = ActiveStatus.USED
                            status.skill_activated[position] = note.timestamp

                case SkillTriggerType.MUTUAL:
                    for period in timetable.periodes:
                        if period.start == note.timestamp and period.status == ActiveStatus.AVAILABLE:
                            period.status = ActiveStatus.USED
                            status.skill_activated[position] = note.timestamp

                case SkillTriggerType.MAGIC:
                    for period in timetable.periodes:
                        if period.start == note.timestamp and period.status == ActiveStatus.AVAILABLE:
                            period.status = ActiveStatus.USED
                            status.skill_activated[position] = note.timestamp

                case _:
                    for period in timetable.periodes:
                        if period.start == note.timestamp and period.status == ActiveStatus.AVAILABLE:
                            period.status = ActiveStatus.USED
                            status.skill_activated[position] = note.timestamp

        debug_message: list[str] = [
            f"{self.__class__.__name__}._substract_life_upon: ",
            f"{note.timestamp * note.time_base:.2f} 秒 - ",
            f"残ライフ値 {status.life.value}, ",
            f"特技発動履歴 {status.skill_activated}",
        ]
        LibsStageLogger.debug("".join(debug_message))

    def _skillcategory_rates(
        self,
        note: Note,
        context: LiveContext,
        status: LiveStatus,
        timetables: list[TimeTable],
    ) -> list[float]:
        """
        ノートの特技系統（参照：列挙クラス ``IndicesSkillCategory``）倍率を計算する。

        まず、ゲストを除くユニットメンバーそれぞれの特技系統の特技効果量を求める。
        その最大値をユニットの特技系統の特技効果量として、特技系統倍率に変換し返す。。
        ただし、センター効果・レゾナンスが有効な場合は、特技系統ごとに全メンバーの総和をユニットの特技効果量とする。

        :param Note note: ノート。
        :param LiveContext context: ライブコンテキスト。
        :param LiveStatus status: ライブステータス。
        :param list[list[TimeTable]] timetables: ゲストを除くユニットメンバーの特技発動時間割。

        :return: 特技系統倍率（スコア系、コンボ系、オルタネイト、ミューチャル、ライフ回復）リスト。
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

        effectvalues: np.ndarray = skillcategory_menber_bonusboost_effectvalues(
            note=note,
            context=context,
            status=status,
            timetables=timetables,
        )

        # ボーナス効果量とブースト効果量の積の効果量に変換する（次元：特技系統、メンバー）。
        effectvalues = bonus_boost.reduce(effectvalues, axis=2)

        # スコア系、コンボ系、オルタネイト系、ミューチャル系と、ライフ回復系を分離。
        status.life.update(int(np.max(effectvalues[SkillCategoryIndices.RECOVERY])))
        effectvalues = effectvalues[: SkillCategoryIndices.RECOVERY]

        # 特技系統の特技効果量をメンバーで比較して最も大きい効果量とする（次元：特技系統）。
        # センター効果・レゾナンスが有効な場合は、特技系統ごとに特技効果量を全て加算する。
        effectvalues = (
            np.add.reduce(effectvalues, axis=1) if context.on_resonance else abs_max.reduce(effectvalues, axis=1)
        )

        debug_message: list[str] = [
            f"{self.__class__.__name__}._skillcategory_rates: ",
            f"{note.timestamp * note.time_base:.2f} 秒の特技系統効果量 - {effectvalues}",
        ]
        LibsStageLogger.debug("".join(debug_message))

        # 特技系統の特技効果量に1.0を加えて特技倍率に変換し、特技系統倍率リストとして返す。
        return (effectvalues + 1.0).tolist()


if __name__ == "__main__":
    print(__file__)
