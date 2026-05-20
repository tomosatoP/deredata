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
  :math:`\\displaystyle \\prod^{特技系統}{特技倍率}`

  - 特技系統（スコアアップ系、COMBOボーナス系、オルタネイト系、ミューチャル系）ごとに、小数点第二位で切り上げる。
  - センター効果・レゾナンス有効時は、発動している特技で効果量を総和する。

:スコアアップ系:
  :math:`1.00+\\{スコアアップ効果量\\times(1.00+スコアアップ効果アップ効果量)\\}`

:COMBOボーナス系:
  :math:`1.00+\\{コンボボーナス効果量\\times(1.00+コンボボーナス効果アップ効果量)\\}`

:オルタネイト:
  :math:`1.00+\\{スコアアップ効果量\\times(1.00+スコアアップ効果アップ効果量)\\}`

  :math:`1.00+\\{コンボボーナスダウン量\\times(1.00+0.00)\\}`

:ミューチャル:
  :math:`1.00+\\{コンボボーナス効果量\\times(1.00+コンボボーナス効果アップ効果量)\\}`

  :math:`1.00+\\{スコアボーナスダウン量\\times(1.00+0.00)\\}`

"""

import numpy as np
from functools import reduce, partial, wraps
from typing import Callable
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


class StageError(Exception):
    """Stageモジュールのエラーハンドラ"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsStageLogger.error(f"StageError: {args}")


class IdexesSkillEffectValue(IntEnum):
    """
    特技系統の列挙クラス。特技効果量リストもしくは配列の添え字に相当する。
    """

    BONUS_SCORE = 0  # スコアボーナス
    BOOST_SCORE = 1  # スコアブースト
    BONUS_ALTERNATE = 2  # オルタネイト（スコアボーナスのコピー）
    BOOST_ALTERNATE = 3  # オルタネイト（極大アップ）
    BONUS_ALTERNATE_DOWN = 4  # オルタネイト（コンボボーナスダウン）
    BOOST_ALTERNATE_DOWN = 5  # オルタネイト（ブースト無し）
    BONUS_COMBO = 6  # COMBOボーナス
    BOOST_COMBO = 7  # COMBOブースト
    BONUS_MUTUAL = 8  # ミューチャル（COMBOボーナスのコピー）
    BOOST_MUTUAL = 9  # ミューチャル（極大アップ）
    BONUS_MUTUAL_DOWN = 10  # ミューチャル（スコアボーナスダウン）
    BOOST_MUTUAL_DOWN = 11  # ミューチャル（ブースト無し）


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
class SkillContext:
    """
    ノートのスコア計算の特技コンテキストのデータクラス。

    :param bool on_resonance: センター効果・レゾナンスが有効かどうか。
    :param float base: 基礎値。
    :param Life life: ライフ。
    :param int position: 特技を有するアイドルのライブ立ち位置（0：センター、1:左隣り、2:右隣り、3:左端、4:右端）。
    :param set[IdolType] unit_type: ゲストを含むユニットメンバーのアイドルタイプの集合。
    :param list[int] list_numbers_by_type:
        ゲストを含むユニットメンバーのアイドルタイプ（ドミナントアイドルタイプを含む）別の人数リスト。
    :param list[int] list_appeals: ユニットメンバー（ゲストを除く）のアピール値（0:ボーカル、1:ダンス、2:ビジュアル）。
    :param list[Skill] list_skills: ユニットメンバー（ゲストを除く）の特技リスト。
    """

    on_resonance: bool = False
    base: float = 0.0
    life: Life = field(default_factory=Life)
    position: int = 0
    livesong_type: SongType = SongType.ALL
    unit_type: set[IdolType] = field(default_factory=set)
    list_numbers_by_type: list[int] = field(default_factory=list)
    list_appeals: list[int] = field(default_factory=list)
    list_skills: list[Skill] = field(default_factory=list)


@dataclass
class TimeTableContext:
    """
    特技発動時間割のコンテキストのデータクラス。

    :param SongType livesong_type: ライブの楽曲タイプ。楽曲要件の判定に用いる。
    :param set[IdolType] unit_type: ゲストを含むユニットメンバーの編成の集合。編成要件の判定に用いる。
    :param int timelimit: 最後のノートの時間（単位時間当たり）。
    :param list[Skill] list_skills: ユニットメンバーの特技リスト。楽曲要件、編成要件を用いる。
    :param list[int] list_intervals: ユニットメンバーの特技の発動間隔（単位時間当たり）のリスト。
    :param list[float] list_probabilities: ``appeals`` で求めたユニットメンバーの特技の発動確率のリスト。
    :param list[int] list_durations: ``appeals`` で求めたユニットメンバーの特技の継続期間（単位時間当たり）のリスト。
    """

    livesong_type: SongType = SongType.ALL
    unit_type: set[IdolType] = field(default_factory=set)
    timelimit: int = 0
    list_skills: list[Skill] = field(default_factory=list)
    list_intervals: list[int] = field(default_factory=list)
    list_probabilities: list[float] = field(default_factory=list)
    list_durations: list[int] = field(default_factory=list)


# 絶対値で比較して大きい方を返すnumpy.ufunc定義
abs_max = np.frompyfunc(lambda x, y: x if abs(x) >= abs(y) else y, 2, 1)


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
    def wrapper(note: Note, context: SkillContext, skillpart: SkillPart, data: np.ndarray) -> np.ndarray:
        """
        特技パーツの特技効果量配列を返す。

        適用メンバー、適用アイコン、適用判定を調べ、効果量を返す。

        :param Note note: スコア計算対象のノート。
        :param SkillContext context: 特技コンテキスト。
        :param SkillPart skillpart: 特技パーツ。
        :param np.ndarray data: 特技パーツの特技効果量配列。

        :return: 特技パーツの特技効果量配列。
        :rtype: np.ndarray
        """

        result = partial(func, note, context, skillpart, data)()
        LibsStageLogger.debug(f"特技パーツ・{skillpart.name}の特技効果量配列: {result}")
        return result

    return wrapper


@wrap_skillpart_effectvalues
def skillpart_bonus_score(note: Note, context: SkillContext, skillpart: SkillPart, data: np.ndarray) -> np.ndarray:
    """
    特技パーツ・スコアボーナスの特技効果量配列を返す。

    :対象特技:
        SCOREボーナス。
        スライドアクト、フリックアクト、ロングアクト。
        キュートフォーカス、クールフォーカス、パッションフォーカス。
        コーディネート、コンセントレーション、オーバーロード。
        トリコロール・スパイク、トリコロール・シナジー。
        ボーカルモチーフ、ダンスモチーフ、ビジュアルモチーフ：ユニットの__アピール値が多いほど。
        ミューチャル：マイナス効果。

    :param Note note: スコア計算対象のノート。
    :param SkillContext context: 特技コンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・スコアボーナスの特技効果量配列。
    :rtype: np.ndarray
    """

    match [skillpart.icon, skillpart.value]:
        case [IconType.NA, float(value)] if value >= 0.0:
            data[IdexesSkillEffectValue.BONUS_SCORE] = value

        case [IconType.NA, float(value)] if value < 0.0:
            data[IdexesSkillEffectValue.BONUS_MUTUAL_DOWN] = value

        case [IconType.NA, str(MOTIF)]:
            match MOTIF:
                case "ユニットのボーカルアピール値が多いほど":
                    data[IdexesSkillEffectValue.BONUS_SCORE] = Simulator._motives.value(context.list_appeals[0])

                case "ユニットのダンスアピール値が多いほど":
                    data[IdexesSkillEffectValue.BONUS_SCORE] = Simulator._motives.value(context.list_appeals[1])

                case "ユニットのビジュアルアピール値が多いほど":
                    data[IdexesSkillEffectValue.BONUS_SCORE] = Simulator._motives.value(context.list_appeals[2])

                case _:
                    LibsStageLogger.error(f"特技パーツ：モチーフの効果量不明。{skillpart.value}")

        case [IconType.SLIDE, float(value)] if note.type in {
            NoteType.SLIDE_ON,
            NoteType.SLIDE_OFF,
            NoteType.SLIDE_PASS,
            NoteType.SLIDE_FLICK_LEFT,
            NoteType.SLIDE_FLICK_RIGHT,
        }:
            data[IdexesSkillEffectValue.BONUS_SCORE] = value

        case [IconType.FLICK, float(value)] if note.type in {
            NoteType.FLICK_LEFT,
            NoteType.FLICK_RIGHT,
            NoteType.SLIDE_FLICK_RIGHT,
            NoteType.SLIDE_FLICK_LEFT,
            NoteType.LONG_FLICK_LEFT,
            NoteType.LONG_FLICK_RIGHT,
        }:
            data[IdexesSkillEffectValue.BONUS_SCORE] = value

        case [IconType.LONG, float(value)] if note.type in {
            NoteType.LONG_ON,
            NoteType.LONG_OFF,
            NoteType.LONG_FLICK_LEFT,
            NoteType.LONG_FLICK_RIGHT,
        }:
            data[IdexesSkillEffectValue.BONUS_SCORE] = value

        case _:
            LibsStageLogger.error(f"特技パーツ：スコアボーナスの条件不適合。{skillpart.icon}, {skillpart.value}")

    return data


@wrap_skillpart_effectvalues
def skillpart_bonus_combo(note: Note, context: SkillContext, skillpart: SkillPart, data: np.ndarray) -> np.ndarray:
    """
    特技パーツ・COMBOボーナスの特技効果量配列を返す。

    :対象特技:
        COMBOボーナス、ライフスパークル。
        キュートフォーカス、クールフォーカス、パッションフォーカス。
        コーディネート、オーバードライブ、オールランド、チューニング。
        トリコロール・スパイク、トリコロール・シナジー。
        オルタネイト（マイナス効果）。

    :param Note note: スコア計算対象のノート。
    :param SkillContext context: 特技コンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・COMBOボーナスの特技効果量配列。
    :rtype: np.ndarray
    """

    data[IdexesSkillEffectValue.BONUS_COMBO] = 0.17
    return data


@wrap_skillpart_effectvalues
def skillpart_support_perfect(note: Note, context: SkillContext, skillpart: SkillPart, data: np.ndarray) -> np.ndarray:
    """
    特技パーツ・PERFECTサポートの特技効果量配列を返す。

    :対象特技: （PERFECTサポート、）チューニング。

    :param Note note: スコア計算対象のノート。
    :param SkillContext context: 特技コンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・PERFECTサポートの特技効果量配列。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_support_combo(note: Note, context: SkillContext, skillpart: SkillPart, data: np.ndarray) -> np.ndarray:
    """
    特技パーツ・COMBOサポートの特技効果量配列を返す。

    :対象特技: （COMBOサポート、）オーバーロード、オーバードライブ。

    :param Note note: スコア計算対象のノート。
    :param SkillContext context: 特技コンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・COMBOサポートの特技効果量配列。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_concentration(note: Note, context: SkillContext, skillpart: SkillPart, data: np.ndarray) -> np.ndarray:
    """
    特技パーツ・集中の特技効果量配列を返す。

    :対象特技: コンセントレーション。

    :param Note note: スコア計算対象のノート。
    :param SkillContext context: 特技コンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・集中の特技効果量配列。
    :rtype: np.ndarray
    """

    return data


@wrap_skillpart_effectvalues
def skillpart_na(note: Note, context: SkillContext, skillpart: SkillPart, data: np.ndarray) -> np.ndarray:
    """
    特技パーツ・非該当の特技効果量配列を返す。

    :対象特技: コンセントレーション。

    :param Note note: スコア計算対象のノート。
    :param SkillContext context: 特技コンテキスト。
    :param SkillPart skillpart: 特技パーツ。
    :param np.ndarray data: 特技パーツの特技効果量配列。

    :return: 特技パーツ・非該当の特技効果量配列。
    :rtype: np.ndarray
    """

    return data


def skill_effectvalue_array(note: Note, context: SkillContext, timetables: list[list[TimeTable]]) -> np.ndarray:
    """
    特技の特技効果量配列を返す。

    - ``context.position`` で指定したアイドルエピソードの特技の特技パーツの特技効果量配列を用意する。
    - 特技発動時間割で特技の発動を確認し、特技パーツの特技効果量配列を埋める。
    - 特技の特技効果量配列に纏め、返す。

    :param Note note: スコア計算対象のノート。
    :param SkillContext context: 特技コンテキスト。
    :param list[list[TimeTable]] timetables: 特技発動時間割のリスト。
    :return: 特技パーツの特技効果量配列。
    :rtype: np.ndarray
    """

    LibsStageLogger.debug(f"特技・{context.list_skills[context.position].skill}を処理。")

    data = np.zeros((len(context.list_skills[context.position].skillparts), len(IdexesSkillEffectValue)))

    # 巻き込みは、timetable.start, timetable.end を加減することで実装可能。
    if any(
        [
            timetable.active and timetable.start <= note.timestamp <= timetable.end
            for timetable in timetables[context.position]
        ]
    ):
        for i, skillpart in enumerate(context.list_skills[context.position].skillparts):
            if skillpart.effect.value in skillpart_effect_funcname:
                data[i] = skillpart_effect_funcname[skillpart.effect](note, context, skillpart, data[i])

    return abs_max.reduce(data)


def wrap_skill_restricted(func: Callable) -> Callable:
    """
    特技の発動要件、楽曲要件、編成要件から発動可否を返す関数のラッパー関数。

    :前処理: デバッグログを出力する。
    :後処理: 無し。

    :param Callable func: 被ラッパー関数。

    :return: 被ラッパー関数
    :rtype: Callable
    """

    @wraps(func)
    def wrapper(note: Note, context: SkillContext) -> bool:
        """
        特技の適用可否を返す。

        楽曲要件、編成要件を満たす場合などは、特技パーツを適用するように **True** を返す。

        :param Note note: スコア計算対象のノート。
        :param SkillContext context: 特技コンテキスト。

        :return:
          **True** であれば、特技発動とする。
          **False** であれば、特技不発とする。
        :rtype: bool
        """

        LibsStageLogger.debug(f"特技・{context.list_skills[context.position].skill}を処理。")

        data = np.zeros((len(context.list_skills[context.position].skillparts), len(IdexesSkillEffectValue)))

        if partial(func, note, context)():
            for i, skillpart in enumerate(context.list_skills[context.position].skillparts):
                if skillpart.effect.value in skillpart_effect_funcname:
                    data[i] = skillpart_effect_funcname[skillpart.effect](note, context, skillpart, data[i])

        return abs_max.reduce(data)

    return wrapper


@wrap_skill_restricted
def skill_restricted_na(note: Note, context: SkillContext) -> bool:
    """
    特技の発動可否を評価する。

    :対象特技:
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
            オーバーロード
            オーバードライブ
            アンコール
            クリスタル・ヒール
            シンデレラマジック
            非該当
            PERFECTサポート
            COMBOサポート

    :特技説明:

    :param Note note: スコア計算対象のノート。
    :param SkillContext context: 特技コンテキスト。

    :return: 特技の発動の判断結果。
    """

    return True


@wrap_skill_restricted
def skill_restricted_unit(note: Note, context: SkillContext) -> bool:
    """
    編成要件のある特技。
        キュートフォーカス、クールフォーカス、パッションフォーカス
        トリコロール・シナジー
        トリコロール・シンフォニー

    :特技説明:

    :param Note note: スコア計算対象のノート。
    :param SkillContext context: 特技コンテキスト。

    :return: 特技パーツ効果を適用するかどうかの判断。
    """

    skill: Skill = context.list_skills[context.position]
    match skill.formation:
        case UnitType.ONLY_CUTE if context.unit_type == {IdolType.CUTE}:
            # キュートフォーカス
            return True

        case UnitType.ONLY_COOL if context.unit_type == {IdolType.COOL}:
            # クールフォーカス
            return True

        case UnitType.ONLY_PASSION if context.unit_type == {IdolType.PASSION}:
            # パッションフォーカス
            return True

        case UnitType.ALL if context.unit_type == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・シナジー
            # トリコロール・シンフォニー
            return True

    return False


@wrap_skill_restricted
def skill_restricted_music(note: Note, context: SkillContext) -> bool:
    """
    楽曲要件のある特技。
        スターライト・アンサンブル

    :特技説明:

    :param Note note: スコア計算対象のノート。
    :param SkillContext context: 特技コンテキスト。

    :return: 特技パーツ効果を適用するかどうかの判断。
    """

    skill: Skill = context.list_skills[context.position]
    match skill.music:
        case MusicType.ALL if context.livesong_type == SongType.ALL:
            # スターライト・アンサンブル
            return True

    return False


@wrap_skill_restricted
def skill_restricted_music_and_unit(note: Note, context: SkillContext) -> bool:
    """
    楽曲要件と編成要件のある特技。
        トリコロール・スパイク
        ドミナント・ハーモニー

    :特技説明:

    :param Note note: スコア計算対象のノート。
    :param SkillContext context: 特技コンテキスト。

    :return: 特技パーツ効果を適用するかどうかの判断。
    """

    skill: Skill = context.list_skills[context.position]
    match [skill.music, skill.formation]:
        case [MusicType.ALL, UnitType.ALL] if context.livesong_type == SongType.ALL and context.unit_type == {
            IdolType.CUTE,
            IdolType.COOL,
            IdolType.PASSION,
        }:
            # トリコロール・スパイク
            return True

        case [MusicType.CUTE, UnitType.ONLY_COOL_AND_CUTE] if (
            context.livesong_type == SongType.CUTE and context.unit_type == {IdolType.CUTE, IdolType.COOL}
        ):
            # ドミナント・ハーモニー
            return True

        case [MusicType.CUTE, UnitType.ONLY_PASSION_AND_CUTE] if (
            context.livesong_type == SongType.CUTE and context.unit_type == {IdolType.CUTE, IdolType.PASSION}
        ):
            # ドミナント・ハーモニー
            return True

        case [MusicType.COOL, UnitType.ONLY_CUTE_AND_COOL] if (
            context.livesong_type == SongType.COOL and context.unit_type == {IdolType.CUTE, IdolType.COOL}
        ):
            # ドミナント・ハーモニー
            return True

        case [MusicType.COOL, UnitType.ONLY_PASSION_AND_COOL] if (
            context.livesong_type == SongType.COOL and context.unit_type == {IdolType.COOL, IdolType.PASSION}
        ):
            # ドミナント・ハーモニー
            return True

    return False


skillpart_effect_funcname: dict[str, Callable] = {
    "スコアボーナス": skillpart_bonus_score,  # ミューチャルのサブは、データ配列の位置が異なり、ブーストもされない
    "COMBOボーナス": skillpart_bonus_combo,  # オルタネイトのサブは、データ配列の位置が異なる、ブーストもされない
    # "スコアブースト": skillpart_boost_score,
    # "COMBOブースト": skillpart_boost_combo,
    # "他特技ブースト": skillpart_boost_other_skill,  # ライフ回復をブースト
    # "特技ブースト": skillpart_boost_skill,  # スコアボーナス、COMBOボーナス、ライフ回復をブースト
    # "スコアボーナスコピー": skillpart_copy_bonus_score,  # リフレインの特技パーツ
    # "COMBOボーナスコピー": skillpart_copy_bonus_combo,  # リフレインの特技パーツ
    # "スコアブーストコピー": skillpart_copy_boost_score,  # オルタネイトのメインの特技パーツ
    # "COMBOブーストコピー": skillpart_copy_boost_combo,  # ミューチャルのメインの特技パーツ
    # "ライフ回復": skillpart_add_life,
    # "ダメージガード": skillpart_no_damage,  # 他の特技のライフ消費を無効化
    # "アンコール": skillpart_encore,  # コピーした特技によって異なる
    # "シンデレラマジック": skillpart_magic,  # コピーした特技によって異なる
    # "ライフ減少量ダウン": skillpart_down_damage,  # クリスタル・ヒール、他の特技のライフ消費を減少
    # "LIVE開始時にライフ回復": skillpart_add_life_at_start,  # クリスタル・ヒール、ライブ開始時のみ発動
    "PERFECTサポート": skillpart_support_perfect,  # 無処理
    "COMBOサポート": skillpart_support_combo,  # 無処理
    "集中": skillpart_concentration,  # 無処理
    "非該当": skillpart_na,  # 無処理
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
    "スターライト・アンサンブル": skill_restricted_music,
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
        ノートのスコア計算のシミュレーションを行う。

        引数は、``アピール値計算`` の出力に対応している。

        :param bool isresonance:
            センター効果・レゾナンスが有効かどうか。
        :param list unit:
            ゲストを含むユニットメンバーのデータリスト。**LiveCarnival** では、ゲストを含まない。

            - エピソード名
            - ボーカルアピール値
            - ダンスアピール値
            - ビジュアルアピール値
            - ライフ値
            - 特技発動確率
            - 特技継続期間（秒）
        :param list supports:
            サポートメンバーのデータリスト。**LiveCarnival** では、不要。

            - エピソード名
            - ボーカルアピール値
            - ダンスアピール値
            - ビジュアルアピール値

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

        skill_context = SkillContext(
            on_resonance=isresonance,
            base=self._base_score_for_note(sum(sum(s) for s in unit[1:4]) + sum(sum(s) for s in supports[1:4])),
            life=Life(value=sum([life for life in unit[4]])),
            livesong_type=self._music.song.type,
            unit_type={episode.type for episode in episodes},
            list_numbers_by_type=[
                number_type(episodes, IdolType.CUTE, DominantType.CUTE),
                number_type(episodes, IdolType.COOL, DominantType.COOL),
                number_type(episodes, IdolType.PASSION, DominantType.PASSION),
            ],
            list_appeals=[sum(appeal[:5]) for appeal in unit[1:4]],
            list_skills=[Simulator._skills.get(episode.skill) for episode in episodes[:5]],
        )

        timetable_context = TimeTableContext(
            livesong_type=self._music.song.type,
            unit_type={episode.type for episode in episodes},
            timelimit=self._music.last_note.timestamp,
            list_skills=[Simulator._skills.get(episode.skill) for episode in episodes[:5]],
            list_intervals=[int(Simulator._skills.get(episode.skill).interval * FPS) for episode in episodes[:5]],
            list_probabilities=unit[5][:5],
            list_durations=[int(timestamp * FPS) for timestamp in unit[6][:5]],
        )
        timetables: list[list[TimeTable]] = self._skill_timetables(timetable_context)

        LibsStageLogger.debug(f"楽曲: {self._music.song.type}タイプ、レベル{self._music.song.level}")
        LibsStageLogger.debug(f"特技: {[skill.skill for skill in skill_context.list_skills]}")
        LibsStageLogger.debug(f"特技発動確率: {timetable_context.list_probabilities}")
        LibsStageLogger.debug(f"特技継続期間: {timetable_context.list_durations}")
        LibsStageLogger.debug(f"基礎値: {skill_context.base}")
        LibsStageLogger.debug(f"初期ライフ: {skill_context.life}")

        LibsStageLogger.info(f"{self.__class__.__name__}.run: シミュレーションを開始。")

        self.combo: int = 0
        return list(
            filter(
                None,
                (
                    self._streaming_note_by_note(note=note, context=skill_context, timetables=timetables)
                    for note in sorted(self._music.notes(include_intervals=1))
                ),
            )
        )

    def _streaming_note_by_note(
        self, note: Note, context: SkillContext, timetables: list[list[TimeTable]]
    ) -> int | None:
        """
        **note** 単位でライブを進める。

        **NoteType** によって、以下のどちらの処理を行う。
            特技発動時にライフ消費判定のある特技発動時間割の更新（カウンターノートを1秒間隔で挿入しておく）。
            ノートのスコア計算。

        :param Note note: スコア計算対象のノート。
        :param SkillContext context: 特技コンテキスト。
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

    def _note_score(self, combo: int, note: Note, context: SkillContext, timetables: list[list[TimeTable]]) -> int:
        """
        ノートのスコアを計算する。

        :ノートのスコア:
          :math:`基礎値\times判定倍率\timesコンボ倍率\times特技倍率`

        :param int combo: コンボ数。
        :param Note note: スコア計算対象のノート。
        :param SkillContext context: 特技計算のコンテキスト。
        :param list[list[TimeTable]] timetables: 特技発動時間割。

        :return: ノートのスコア。
        :rtype: int
        """

        def ceil2(value: float) -> float:
            """
            小数点第二位で切り上げ。

            :param float value: 小数点第二位で切り上げたい値
            :return: value を小数点第二位で切り上げ
            :rtype: float
            """

            return ceil(value * 100.0) / 100.0

        def skillcategory_rate(values: list[float]) -> float:
            """
            特技系統の特技倍率を計算。

            :特技系統: スコアアップ、オルタネイト（ブースト、ダウン）、COMBOボーナス、ミューチャル（ブースト、ダウン）
              :math:`1.0+ボーナス効果量\times(1.0+ブースト効果量)`

            :param list[float] values: 特技系統の効果量（ボーナス、ブースト）
            :return: 特技系統の特技倍率
            :rtype: float
            """

            return 1.0 + ceil2(values[0] * (1.0 + values[1]))

        # 特技の特技効果量リストを求める。
        skill_rates: list[float] = self._skill_effectvalues(note=note, context=context, timetables=timetables)

        return round(
            context.base  # 基礎値
            * self._perfection_rate("PERFECT")  # 判定倍率
            * Simulator._comborates.rate(combo / self._music.note_number)  # コンボ倍率
            * reduce(
                mul,
                [
                    skillcategory_rate(skill_rates[x : x + 2])
                    for x in [a.value for a in list(IdexesSkillEffectValue) if not a.value % 2]
                ],
            )  # 特技倍率（特技効果量リストから特技系統ごとの特技倍率を求め、掛け合わせる）
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
        判定倍率。

        判定倍率は、ノートの判定によって決まる値のこと。
        ここでは、 ``PERFECT`` のみのフルコンボとして簡略化している。

        :param str perfection: ノート判定
        :return: 判定倍率
        :rtype: float
        """

        return 1.0

    def _skill_timetables(self, context: TimeTableContext) -> list[list[TimeTable]]:
        """
        ユニットメンバー（ゲストを除く）の特技発動タイムテーブルを作成する。

        特技の発動要件・楽曲要件・編成要件を満たし、特技発動確率が乱数値以上の時に発動する。
        ただし、残ライフ値が判らないので、発動要件 **ライフを〇消費** は暫定で :math:`active=True` とする。
        最後のノートの3秒前までが、特技発動の限界。

        :param TimeTableContext context: 特技発動時間割のコンテキスト。

        :return: 特技発動タイムテーブル。
        :rtype: list[list[TimeTable]]
        """

        all_set: set[IdolType] = {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}
        only_cute_set: set[IdolType] = {IdolType.CUTE}
        only_cool_set: set[IdolType] = {IdolType.COOL}
        only_passion_set: set[IdolType] = {IdolType.PASSION}
        only_cute_and_cool_set: set[IdolType] = {IdolType.CUTE, IdolType.COOL}
        only_cute_and_passion_set: set[IdolType] = {IdolType.CUTE, IdolType.PASSION}
        only_cool_and_passion_set: set[IdolType] = {IdolType.COOL, IdolType.PASSION}

        timetables: list = list()

        # ユニットメンバーの特技時間割
        for imember, skill in enumerate(context.list_skills):
            # 初回、特技は発動しない。
            # :todo: クリスタル・ヒールは初回に発動（発動間隔が 0）するだけ。
            timetable: list = [TimeTable(active=False, start=0, end=int(context.list_durations[imember]))]

            jcycle: int = 1
            while skill.interval != 0 and (context.timelimit - 3 * FPS) > context.list_intervals[imember] * jcycle:
                # 特技発動間隔が 0 の場合は、次回以降の特技時間割が不要
                # 初回より後から、最後のノートの3秒前までの特技時間割を作成

                pass_song_and_unit: bool = False  # 特技の発動／不発
                match [skill.music, skill.formation]:
                    # 楽曲要件、編成要件で検索し、特技の発動／不発を決定する。

                    case [MusicType.NA, UnitType.NA]:
                        # ライフ消費のある特技：オーバーロード

                        pass_song_and_unit = True

                    case [MusicType.NA, UnitType.ALL] if context.unit_type == all_set:
                        # トリコロール・シナジー
                        # トリコロール・シンフォニー

                        pass_song_and_unit = True

                    case [MusicType.NA, UnitType.ONLY_CUTE] if context.unit_type == only_cute_set:
                        # キュートフォーカス

                        pass_song_and_unit = True

                    case [MusicType.NA, UnitType.ONLY_COOL] if context.unit_type == only_cool_set:
                        # クールフォーカス

                        pass_song_and_unit = True

                    case [MusicType.NA, UnitType.ONLY_PASSION] if context.unit_type == only_passion_set:
                        # パッションフォーカス

                        pass_song_and_unit = True

                    case [MusicType.ALL, UnitType.NA] if context.livesong_type == SongType.ALL:
                        # スターライト・アンサンブル

                        pass_song_and_unit = True

                    case [MusicType.ALL, UnitType.ALL] if (
                        context.livesong_type == SongType.ALL and context.unit_type == all_set
                    ):
                        # ライフ消費のある特技：トリコロール・スパイク

                        pass_song_and_unit = True

                    case [MusicType.CUTE, UnitType.ONLY_COOL_AND_CUTE] if (
                        context.livesong_type == SongType.CUTE and context.unit_type == only_cute_and_cool_set
                    ):
                        # ドミナント・ハーモニー（キュートドミナントアイドル＋クールアイドル）

                        pass_song_and_unit = True

                    case [MusicType.CUTE, UnitType.ONLY_PASSION_AND_CUTE] if (
                        context.livesong_type == SongType.CUTE and context.unit_type == only_cute_and_passion_set
                    ):
                        # ドミナント・ハーモニー（キュートドミナントアイドル＋パッションアイドル）

                        pass_song_and_unit = True

                    case [MusicType.COOL, UnitType.ONLY_CUTE_AND_COOL] if (
                        context.livesong_type == SongType.COOL and context.unit_type == only_cute_and_cool_set
                    ):
                        # ドミナント・ハーモニー（クールドミナントアイドル＋キュートアイドル）

                        pass_song_and_unit = True

                    case [MusicType.COOL, UnitType.ONLY_PASSION_AND_COOL] if (
                        context.livesong_type == SongType.COOL and context.unit_type == only_cool_and_passion_set
                    ):
                        # ドミナント・ハーモニー（クールドミナントアイドル＋パッションアイドル）

                        pass_song_and_unit = True

                    case [MusicType.PASSION, UnitType.ONLY_CUTE_AND_PASSION] if (
                        context.livesong_type == SongType.PASSION and context.unit_type == only_cute_and_passion_set
                    ):
                        # ドミナント・ハーモニー（パッションドミナントアイドル＋キュートアイドル）

                        pass_song_and_unit = True

                    case [MusicType.PASSION, UnitType.ONLY_COOL_AND_PASSION] if (
                        context.livesong_type == SongType.PASSION and context.unit_type == only_cool_and_passion_set
                    ):
                        # ドミナント・ハーモニー（パッションドミナントアイドル＋クールアイドル）

                        pass_song_and_unit = True

                    case _:
                        LibsStageLogger.debug(
                            f"{self.__class__.__name__}._skill_timetables: {skill.music}/{skill.formation} 漏れ"
                        )

                timetable.append(
                    TimeTable(
                        active=True if random() < context.list_probabilities[imember] and pass_song_and_unit else False,
                        start=context.list_intervals[imember] * jcycle,
                        end=context.list_intervals[imember] * jcycle + context.list_durations[imember],
                    )
                )
                jcycle += 1
            timetables.append(timetable)

        return timetables

    def _skill_effectvalues(self, note: Note, context: SkillContext, timetables: list[list[TimeTable]]) -> list[float]:
        """
        特技効果量を計算する。

        ユニットメンバー（ゲストを除く）の特技の計12要素（参照：列挙クラス ``IdexesSkillEffectValueArray``）の
        特技効果量を求め、要素ごとにメンバーの最大値を求めユニットの特技効果量のリストとする。
        ただし、センター効果・レゾナンスが有効な場合は、要素ごとに全メンバーの総和を求め特技効果量のリストとする。

        :param Note note: ノート。
        :param SkillContext context: 特技コンテキスト。
        :param list[list[TimeTable]] timetables: ユニットメンバー（ゲストを除く）の特技発動時間割。

        :return: 特技系統別効果量のリスト
        :rtype: list[float]
        """

        effectvaluearray: np.ndarray = np.zeros((len(context.list_skills), len(IdexesSkillEffectValue)))
        for position, skill in enumerate(context.list_skills):
            # 特技発動中のメンバーのライブ立ち位置を特技コンテキストにセットして、特技の特技効果量配列を得る。
            context.position = position
            effectvaluearray[position] = skill_effectvalue_array(note=note, context=context, timetables=timetables)

        # 特技効果量配列を最も効果の大きい要素にする。
        # センター効果・レゾナンスが有効な場合は、特技効果量配列の要素を全て加算する。
        result = np.add.reduce(effectvaluearray) if context.on_resonance else abs_max.reduce(effectvaluearray)
        return result.tolist()


if __name__ == "__main__":
    print(__file__)
