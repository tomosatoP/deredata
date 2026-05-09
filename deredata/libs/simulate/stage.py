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
from deredata.libs.database.skills import Skill, Skills, EffectType, IconType
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


class SkillValueIndices(IntEnum):
    """
    特技系統の列挙クラス。特技効果量配列の添え字に相当する。
    """

    BONUS_SCORE = 0  # スコアボーナス
    BOOST_SCORE = 1  # スコアブースト
    BONUS_ALTERNATE = 2  # オルタネイト（スコアボーナスのコピー）
    BOOST_ALTERNATE = 3  # オルタネイト（極大アップ）
    BONUS_ALTERNATE1 = 4  # オルタネイト（コンボボーナスダウン）
    BOOST_ALTERNATE1 = 5  # オルタネイト（ブースト無し）
    BONUS_COMBO = 6  # COMBOボーナス
    BOOST_COMBO = 7  # COMBOブースト
    BONUS_MUTUAL = 8  # ミューチャル（COMBOボーナスのコピー）
    BOOST_MUTUAL = 9  # ミューチャル（極大アップ）
    BONUS_MUTUAL1 = 10  # ミューチャル（スコアボーナスダウン）
    BOOST_MUTUAL1 = 11  # ミューチャル（ブースト無し）


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
class SkillpartContext:
    """
    ノートのスコア計算の特技パーツコンテキストのデータクラス。

    :param bool on_resonance: センター効果・レゾナンスが有効かどうか。
    :param Life life: ライフ。
    :param list[int] number_typelist:
      ゲストを含むユニットメンバーのアイドルタイプ（ドミナントアイドルタイプを含む）別の人数リスト。
    :param list[int] appeal_list: ユニットメンバー（ゲストを除く）のアピール値（ボーカル、ダンス、ビジュアル）。
    :param list[Skill] skill_list: ユニットメンバー（ゲストを除く）の特技リスト。
    """

    pass


@dataclass
class SkillContext:
    """
    ノートのスコア計算の特技コンテキストのデータクラス。

    :param bool on_resonance: センター効果・レゾナンスが有効かどうか。
    :param float base: 基礎値。
    :param Life life: ライフ。
    :param list[int] number_typelist:
      ゲストを含むユニットメンバーのアイドルタイプ（ドミナントアイドルタイプを含む）別の人数リスト。
    :param list[int] appeal_list: ユニットメンバー（ゲストを除く）のアピール値（ボーカル、ダンス、ビジュアル）。
    :param list[Skill] skill_list: ユニットメンバー（ゲストを除く）の特技リスト。
    """

    on_resonance: bool = False  # センター効果・レゾナンスが有効かどうか。
    base: float = 0.0  # 基礎値。
    life: Life = field(default_factory=Life)  # ライフ。
    number_typelist: list[int] = field(default_factory=list)  # タイプ別の人数リスト
    appeal_list: list[int] = field(default_factory=list)  # ユニットメンバー（ゲストを除く）のアピール値
    skill_list: list[Skill] = field(default_factory=list)  # ユニットメンバー（ゲストを除く）の特技リスト


@dataclass
class TimeTableContext:
    """
    特技発動時間割のコンテキストのデータクラス。

    :param SongType livesong_type: ライブの楽曲タイプ。楽曲要件の判定に用いる。
    :param set[IdolType] unit_type: ゲストを含むユニットメンバーの編成の集合。編成要件の判定に用いる。
    :param int timelimit: 最後のノートの時間（単位時間当たり）。
    :param list[Skill] skill_list: ユニットメンバーの特技リスト。楽曲要件、編成要件を用いる。
    :param list[int] interval_list: ユニットメンバーの特技の発動間隔（単位時間当たり）のリスト。
    :param list[float] probability_list: ``appeals`` で求めたユニットメンバーの特技の発動確率のリスト。
    :param list[int] duration_list: ``appeals`` で求めたユニットメンバーの特技の継続期間（単位時間当たり）のリスト。
    """

    livesong_type: SongType = SongType.ALL
    unit_type: set[IdolType] = field(default_factory=set)
    timelimit: int = 0
    skill_list: list[Skill] = field(default_factory=list)
    interval_list: list[int] = field(default_factory=list)
    probability_list: list[float] = field(default_factory=list)
    duration_list: list[int] = field(default_factory=list)


# 絶対値で比較して大きい方を返すnumpy.ufunc定義
abs_max = np.frompyfunc(lambda x, y: x if abs(x) >= abs(y) else y, 2, 1)


def skillpartwrap(func: Callable) -> Callable:
    """
    特技パーツ効果量データ配列を返すラッパー関数。

    :前処理: 特技パーツ効果量データ配列を初期化する。
    :後処理: 無し。

    :param Callable func: ラッパー関数。

    :return: ラッパー関数。
    :rtype: Callable
    """

    @wraps(func)
    def wrapper(note: Note, context: SkillpartContext) -> np.ndarray:
        """
        特技パーツ効果の関数。

        適用メンバー、適用アイコン、適用判定を調べ、効果量を返す。

        :param Note note: スコア計算対象のノート。
        :param SkillContext context: 特技パーツコンテキスト。

        :return: 特技パーツ効果量データ配列。
        :rtype: np.ndarray
        """

        data = np.zeros(len(SkillValueIndices))
        result = partial(func, note, context, data)()

        return result

    return wrapper


@skillpartwrap
def skillpart_bonus_score(note: Note, context: SkillpartContext, data: np.ndarray) -> np.ndarray:

    data[SkillValueIndices.BONUS_SCORE] = 0.17
    return data


@skillpartwrap
def skillpart_support_perfect(note: Note, context: SkillpartContext, data: np.ndarray) -> np.ndarray:
    return data


def skillwrap(func: Callable) -> Callable:
    """
    特技の効果量配列を返すラッパー関数。

    他の特技に影響する特技は、重複を考慮する。

        - トリコロール・シンフォニーの他特技ブースト。
            - ライフ回復、ダメージガード
        - アンコール
        - シンデレラマジック

    スコア計算に影響しないので、重複を考慮しない。

        - PERFECTサポート、COMBOサポート、集中。

    特技のノートへの適用でライフ消費は無い（スコア計算に影響しない）ので、重複を考慮しない。

        - ダメージガード発動中は、ライフ消費無し（ただし、ブーストのライフ回復は考慮する）
        - クリスタル・ヒールは、ライフ消費50%OFF。

    :前処理: 特技パーツ分の特技効果量配列を初期化する。
    :後処理: 特技効果量配列を最も効果の大きい要素にする。

    :param Callable func: ラッパー関数。

    :return: ラッパー関数
    :rtype: Callable
    """

    @wraps(func)
    def wrapper(note: Note, position: int, context: SkillContext) -> bool:
        """
        特技の関数。

        楽曲要件、編成要件を満たす場合は、特技パーツ効果を呼び出すように **True** を返す。

        :param Note note: スコア計算対象のノート。
        :param int position: 本特技のアイドルのライブ立ち位置（0：センター、1:左隣り、2:右隣り、3:左端、4:右端）。
        :param SkillContext context: 特技コンテキスト。

        :return:
          **True** であれば、特技パーツ効果を呼び出して特技効果量データ配列に効果量を格納する。
          **False** であれば、初期化済みの特技効果量データ配列をそのまま。
        :rtype: bool
        """

        LibsStageLogger.debug(f"特技・{context.skill_list[position].skill}を処理。")

        data = np.zeros((len(context.skill_list[position].skillparts), len(SkillValueIndices)))

        if partial(func, note, position, context)():
            for i, skillpart in enumerate(context.skill_list[position].skillparts):
                if skillpart.effect in effect_funcname:
                    data[i] = effect_funcname[skillpart.effect](note, SkillpartContext())

        return abs_max.reduce(data)

    return wrapper


@skillwrap
def skill_score_bonus(note: Note, position: int, context: SkillContext) -> bool:
    """
    スコアボーナス系特技。

    :特技説明:
        __秒毎、__確率で__間、PERFECTのスコア__%アップ
        __秒毎、__確率で__間、PERFECTのスコア__%アップ、フリックアイコンなら__%アップ
        __秒毎、__確率で__間、PERFECTのスコア__%アップ、スライドアイコンなら__%アップ
        __秒毎、__確率で__間、PERFECTのスコア__%アップ、ロングアイコンなら__%アップ

    :param Note note: スコア計算対象のノート。
    :param int position: 本特技のアイドルのライブ立ち位置（0：センター、1:左隣り、2:右隣り、3:左端、4:右端）。
    :param SkillContext context: 特技コンテキスト。

    :return: 特技パーツ効果を呼び出すかどうかの判断。
    """

    # 特技は発動済みなので、楽曲要件・編成要件をチェック
    # 特技・SCOREボーナスには、楽曲要件・編成要件無し

    return True


@skillwrap
def skill_perfect_support(note: Note, position: int, context: SkillContext) -> bool:
    """
    PERFECTサポート系特技。

    :特技説明:
        __秒毎、__確率で__間、__をPERFECTにする

    :param Note note: スコア計算対象のノート。
    :param int position: 本特技のアイドルのライブ立ち位置（0：センター、1:左隣り、2:右隣り、3:左端、4:右端）。
    :param SkillContext context: 特技コンテキスト。

    :return: 特技パーツ効果を呼び出すかどうかの判断。
    """

    return False


effect_funcname: dict[str, Callable] = {
    "スコアボーナス": skillpart_bonus_score,
    "PERFECTサポート": skillpart_support_perfect,
}

skill_funcname: dict[str, Callable] = {
    # skill_score_bonus
    "SCOREボーナス": skill_score_bonus,
    "フリックアクト": skill_score_bonus,
    "スライドアクト": skill_score_bonus,
    "ロングアクト": skill_score_bonus,
    # skill_perfect_support
    "PERFECTサポート": skill_perfect_support,
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
            base=self._base(sum(sum(s) for s in unit[1:4]) + sum(sum(s) for s in supports[1:4])),
            life=Life(value=sum([life for life in unit[4]])),
            number_typelist=[
                number_type(episodes, IdolType.CUTE, DominantType.CUTE),
                number_type(episodes, IdolType.COOL, DominantType.COOL),
                number_type(episodes, IdolType.PASSION, DominantType.PASSION),
            ],
            appeal_list=[sum(appeal[:5]) for appeal in unit[1:4]],
            skill_list=[Simulator._skills.get(episode.skill) for episode in episodes[:5]],
        )

        timetable_context = TimeTableContext(
            livesong_type=self._music.song.type,
            unit_type={episode.type for episode in episodes},
            timelimit=self._music.last_note.timestamp,
            skill_list=[Simulator._skills.get(episode.skill) for episode in episodes[:5]],
            interval_list=[int(Simulator._skills.get(episode.skill).interval * FPS) for episode in episodes[:5]],
            probability_list=unit[5][:5],
            duration_list=[int(timestamp * FPS) for timestamp in unit[6][:5]],
        )
        timetables: list[list[TimeTable]] = self._skill_timetables(timetable_context)

        LibsStageLogger.debug(f"楽曲: {self._music.song.type}タイプ、レベル{self._music.song.level}")
        LibsStageLogger.debug(f"特技: {[skill.skill for skill in skill_context.skill_list]}")
        LibsStageLogger.debug(f"特技発動確率: {timetable_context.probability_list}")
        LibsStageLogger.debug(f"特技継続期間: {timetable_context.duration_list}")
        LibsStageLogger.debug(f"基礎値: {skill_context.base}")
        LibsStageLogger.debug(f"初期ライフ: {skill_context.life}")

        LibsStageLogger.info(f"{self.__class__.__name__}.run: シミュレーションを開始。")

        return list(
            filter(
                None,
                (
                    self._streaming(note=note, context=skill_context, timetables=timetables)
                    for note in sorted(self._music.notes(include_intervals=1))
                ),
            )
        )

    def _streaming(self, note: Note, context: SkillContext, timetables: list[list[TimeTable]]) -> int | None:
        """
        **note** 単位でライブを進める。

        **NoteType** によって、以下のどちらの処理を行う。
            特技発動時にライフ消費判定のある特技発動時間割の更新（カウンターノートを1秒間隔で挿入しておく）。
            ノートのスコア計算。

        :param Note note: スコア計算対象のノート。
        :param SkillContext context: 特技計算のコンテキスト。
        :param list[list[TimeTable]] timetables: 特技発動時間割。

        :return: ノートのスコア。
        :rtype: int
        """

        combo: int = 0

        match note.type:
            case NoteType.COUNT:
                # 特技発動時間割を更新（ライフ消費などの際）。
                return None

            case _:
                # ノートのスコアを計算。

                combo += 1  # コンボ継続
                return self._score(combo, note, context, timetables)

    def _score(self, combo: int, note: Note, context: SkillContext, timetables: list[list[TimeTable]]) -> int:
        """
        ノートのスコア計算。

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

        def series(values: list[float]) -> float:
            """
            特技系統の特技倍率の計算。

            :特技系統: スコアアップ、オルタネイト（ブースト、ダウン）、COMBOボーナス、ミューチャル（ブースト、ダウン）
              :math:`1.0+ボーナス効果量\times(1.0+ブースト効果量)`

            :param list[float] values: 特技系統の効果量（ボーナス、ブースト）
            :return: 特技系統の特技倍率
            :rtype: float
            """

            return 1.0 + ceil2(values[0] * (1.0 + values[1]))

        skill_rates: list[float] = self._skill_values(note=note, context=context, timetables=timetables)

        return round(
            context.base  # 基礎値
            * self._perfection_rate("PERFECT")  # 判定倍率
            * Simulator._comborates.rate(combo / self._music.note_number)  # コンボ倍率
            * reduce(
                mul,
                [series(skill_rates[x : x + 2]) for x in [a.value for a in list(SkillValueIndices) if not a.value % 2]],
            )  # 特技倍率（特技効果量データ配列を連続2要素ずつの配列に分けて個々の特技倍率を求め、掛け合わせる）
        )

    def _base(self, appeals: int) -> float:
        """
        ノートの基礎値を計算。

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
        for imember, skill in enumerate(context.skill_list):
            # 初回、特技は発動しない。
            # :todo: クリスタル・ヒールは初回に発動（発動間隔が 0）するだけ。
            timetable: list = [TimeTable(active=False, start=0, end=int(context.duration_list[imember]))]

            jcycle: int = 1
            while skill.interval != 0 and (context.timelimit - 3 * FPS) > context.interval_list[imember] * jcycle:
                # 特技発動間隔が 0 の場合は、次回以降の特技時間割が不要
                # 初回より後から、最後のノートの3秒前までの特技時間割を作成

                pass_song_and_unit: bool = False  # 特技の発動／不発
                match [skill.music, skill.formation]:
                    # 楽曲要件、編成要件で検索し、特技の発動／不発を決定する。

                    case [MusicType.NA, UnitType.NA]:
                        pass_song_and_unit = True

                    case [MusicType.NA, UnitType.ALL] if context.unit_type == all_set:
                        pass_song_and_unit = True

                    case [MusicType.NA, UnitType.ONLY_CUTE] if context.unit_type == only_cute_set:
                        pass_song_and_unit = True

                    case [MusicType.NA, UnitType.ONLY_COOL] if context.unit_type == only_cool_set:
                        pass_song_and_unit = True

                    case [MusicType.NA, UnitType.ONLY_PASSION] if context.unit_type == only_passion_set:
                        pass_song_and_unit = True

                    case [MusicType.ALL, UnitType.NA] if context.livesong_type == SongType.ALL:
                        pass_song_and_unit = True

                    case [MusicType.ALL, UnitType.ALL] if (
                        context.livesong_type == SongType.ALL and context.unit_type == all_set
                    ):
                        pass_song_and_unit = True

                    case [MusicType.CUTE, UnitType.ONLY_COOL_AND_CUTE] if (
                        context.livesong_type == SongType.CUTE and context.unit_type == only_cute_and_cool_set
                    ):
                        pass_song_and_unit = True

                    case [MusicType.CUTE, UnitType.ONLY_PASSION_AND_CUTE] if (
                        context.livesong_type == SongType.CUTE and context.unit_type == only_cute_and_passion_set
                    ):
                        pass_song_and_unit = True

                    case [MusicType.COOL, UnitType.ONLY_CUTE_AND_COOL] if (
                        context.livesong_type == SongType.COOL and context.unit_type == only_cute_and_cool_set
                    ):
                        pass_song_and_unit = True

                    case [MusicType.COOL, UnitType.ONLY_PASSION_AND_COOL] if (
                        context.livesong_type == SongType.COOL and context.unit_type == only_cool_and_passion_set
                    ):
                        pass_song_and_unit = True

                    case [MusicType.PASSION, UnitType.ONLY_CUTE_AND_PASSION] if (
                        context.livesong_type == SongType.PASSION and context.unit_type == only_cute_and_passion_set
                    ):
                        pass_song_and_unit = True

                    case [MusicType.PASSION, UnitType.ONLY_COOL_AND_PASSION] if (
                        context.livesong_type == SongType.PASSION and context.unit_type == only_cool_and_passion_set
                    ):
                        pass_song_and_unit = True

                    case _:
                        LibsStageLogger.debug(
                            f"{self.__class__.__name__}._skill_timetables: {skill.music}/{skill.formation} 漏れ"
                        )

                timetable.append(
                    TimeTable(
                        active=True if random() < context.probability_list[imember] and pass_song_and_unit else False,
                        start=context.interval_list[imember] * jcycle,
                        end=context.interval_list[imember] * jcycle + context.duration_list[imember],
                    )
                )
                jcycle += 1
            timetables.append(timetable)

        return timetables

    def _skill_values(self, note: Note, context: SkillContext, timetables: list[list[TimeTable]]) -> list[float]:
        """
        特技系統別の効果量リスト。

        特技系統は4種在り、特技系統別の特技効果を積算した値が特技倍率。
        それぞれの特技効果にボーナスとブーストがあって、計12要素の特技効果量データ配列に格納する。
        列挙クラス ``SkillValueIndices`` も参照。

        特技系統別の効果量リストの内訳は、特技効果量データ配列の順で次の通り。
            :BONUS_SCORE: 0: スコアボーナスの効果量。
            :BOOST_SCORE: 1: スコアブーストの効果量。
            :BONUS_ALTERNATE: 2: オルタネイト
            :BOOST_ALTERNATE: 3:
            :BONUS_ALTERNATE1: 4:
            :BOOST_ALTERNATE1: 5:
            :BONUS_COMBO: 6: COMBOボーナスの効果量。
            :BOOST_COMBO: 7: COMBOブーストの効果量。
            :BONUS_MUTUAL: 8: ミューチャル
            :BOOST_MUTUAL: 9:
            :BONUS_MUTUAL1: 10:
            :BOOST_MUTUAL1: 11:

        :param Note note: ノート。
        :param SkillContext context: 特技計算のコンテキスト。
        :param list[list[TimeTable]] timetables: ユニットメンバー（ゲストを除く）の特技発動時間割。

        :return: 特技系統別効果量のリスト
        :rtype: list[float]
        """

        for position, skill in enumerate(context.skill_list):
            if any(
                timetable.active
                for timetable in timetables[position]
                if timetable.start <= note.timestamp <= timetable.end
            ):
                # 特技発動時間割で特技発動中を確認

                if skill.skill in skill_funcname:
                    result: np.ndarray = skill_funcname[skill.skill](note, position, context)
                else:
                    LibsStageLogger.error(f"{self.__class__.__name__}._skill_values: {skill.skill}は、未実装です。")

        # :todo: ユニット分の特技効果データ配列を集計
        return result.tolist() if "result" in locals() else [0.0 for _ in range(len(SkillValueIndices))]

    def _skill_values_old(self, note: Note, context: SkillContext, timetables: list[list[TimeTable]]) -> list[float]:
        """
        特技系統別の効果量リスト。

        特技系統は4種在り、特技系統別の特技効果を積算した値が特技倍率。
        それぞれの特技効果にボーナスとブーストがあって、計12要素の特技効果量データ配列に格納する。
        列挙クラス ``SkillValueIndices`` も参照。

        特技系統別の効果量リストの内訳は、特技効果量データ配列の順で次の通り。
            :BONUS_SCORE: 0: スコアボーナスの効果量。
            :BOOST_SCORE: 1: スコアブーストの効果量。
            :BONUS_ALTERNATE: 2: オルタネイト
            :BOOST_ALTERNATE: 3:
            :BONUS_ALTERNATE1: 4:
            :BOOST_ALTERNATE1: 5:
            :BONUS_COMBO: 6: COMBOボーナスの効果量。
            :BOOST_COMBO: 7: COMBOブーストの効果量。
            :BONUS_MUTUAL: 8: ミューチャル
            :BOOST_MUTUAL: 9:
            :BONUS_MUTUAL1: 10:
            :BOOST_MUTUAL1: 11:

        :param Note note: ノート。
        :param SkillContext context: 特技計算のコンテキスト。
        :param list[list[TimeTable]] timetables: ユニットメンバー（ゲストを除く）の特技発動時間割。

        :return: 特技系統別効果量のリスト
        :rtype: list[float]
        """

        abs_max = partial(max, key=abs)

        # 発動要件/TriggerType（特技発動時間割に組み込み済み：楽曲要件/MusicType, 編成要件/UnitType）
        # 適用メンバー/IdolType, 適用アイコン/IconType（PERFECTのみ：適用判定/PerfectionType）

        # 他特技ボーナス（BONUS_SCORE、BONUS_COMBO以外）とは、
        #   ライフ回復系
        #     ADD_LIFE
        #     NO_DAMAGE
        #     DOWN_DAMAGE
        #     ブースト対象外: ADD_LIFE_AT_START（LIVE開始時にライフを200%まで回復）
        #   非ライフ回復系
        #     SUPPORT_PERFECT
        #     ブースト対象外: CONCENTRATION（PERFECT判定される時間が短くなる）
        #     ブースト対象外: SUPPORT_COMBO（PERFECT判定のみCOMBO継続）
        skill_values: list[list[float]] = [[0.0 for _ in range(len(SkillValueIndices))]]

        # 保留する回復ライフ値。
        life: list[int] = list()
        # 回復ライフ値をブーストする量。
        life_boost: list[float] = list()
        # life(1.0 )

        for position, skill in enumerate(context.skill_list):
            # メンバーごとの特技（順序：センター、左隣、右隣、左端、右端）

            if any(
                timetable.active
                for timetable in timetables[position]
                if timetable.start <= note.timestamp <= timetable.end
            ):
                # 特技発動時間割で特技発動中を確認

                LibsStageLogger.debug(f"  {position}人目の特技 {skill.skill} 発動")

                # 特技バーツ効果量リスト
                skillpart_values: list[list[float]] = list()

                for iskillpart, skillpart in enumerate(skill.skillparts):
                    # 特技パーツごと（順不同）

                    skillpart_values.append([0.0 for _ in range(len(SkillValueIndices))])
                    match skillpart.effect:
                        # 特技パーツ効果で検索

                        case EffectType.BONUS_SCORE:
                            # スコアアップ
                            # PERFECT判定のみ（Full Combo/All Perfect）なので、PERFECT判定と非該当のみ。
                            # GREAT/NICE/BAD/MISS判定は、対処しない。

                            match [skillpart.icon, skillpart.value]:
                                # 適用アイコン、効果量で検索

                                case [IconType.NA, float(value)] if value >= 0.0:
                                    # SCOREボーナス／効果量ブースト
                                    # コーディネート／効果量ブースト
                                    # スライドアクト（非スライド）／効果量ブースト
                                    # ロングアクト（非ロング）／効果量ブースト
                                    # フリックアクト（非フリック）／効果量ブースト
                                    # オーバーロード／効果量ブースト
                                    # コンセントレーション／効果量ブースト
                                    # キュートフォーカス、クールフォーカス、パッションフォーカス／効果量ブースト
                                    # コーディネート／効果量ブースト
                                    # トリコロール・シナジー／効果量ブースト
                                    # トリコロール・スパイク（ライフを**消費して）／効果量ブースト

                                    skillpart_values[iskillpart][SkillValueIndices.BONUS_SCORE] = value

                                case [IconType.NA, float(value)] if value < 0.0:
                                    # ミューチャル（20%ダウン）／ブースト無し

                                    skillpart_values[iskillpart][SkillValueIndices.BONUS_MUTUAL1] = value

                                case [IconType.NA, str(MOTIF)]:
                                    # ボーカルモチーフ、ダンスモチーフ、ビジュアルモチーフ／効果量ブースト

                                    match MOTIF:
                                        # 効果量を示す文字列

                                        case "ユニットボーカルアピール値が多いほど":
                                            skillpart_values[iskillpart][SkillValueIndices.BONUS_SCORE] = (
                                                Simulator._motives.value(context.appeal_list[0])
                                            )

                                        case "ユニットダンスアピール値が多いほど":
                                            skillpart_values[iskillpart][SkillValueIndices.BONUS_SCORE] = (
                                                Simulator._motives.value(context.appeal_list[1])
                                            )

                                        case "ユニットビジュアルアピール値が多いほど":
                                            skillpart_values[iskillpart][SkillValueIndices.BONUS_SCORE] = (
                                                Simulator._motives.value(context.appeal_list[2])
                                            )

                                        case _:
                                            LibsStageLogger.error(f"モチーフの不一致: {MOTIF}")

                                case [IconType.SLIDE, float(value)] if note.type in {
                                    NoteType.SLIDE_ON,
                                    NoteType.SLIDE_OFF,
                                    NoteType.SLIDE_PASS,
                                    NoteType.SLIDE_FLICK_LEFT,
                                    NoteType.SLIDE_FLICK_RIGHT,
                                }:
                                    # スライドアクト（スライドノート）／効果量ブースト

                                    skillpart_values[iskillpart][SkillValueIndices.BONUS_SCORE] = value

                                case [IconType.FLICK, float(value)] if note.type in {
                                    NoteType.FLICK_LEFT,
                                    NoteType.FLICK_RIGHT,
                                    NoteType.SLIDE_FLICK_RIGHT,
                                    NoteType.SLIDE_FLICK_LEFT,
                                    NoteType.LONG_FLICK_LEFT,
                                    NoteType.LONG_FLICK_RIGHT,
                                }:
                                    # フリックアクト（フリックノート）／効果量ブースト

                                    skillpart_values[iskillpart][SkillValueIndices.BONUS_SCORE] = value

                                case [IconType.LONG, float(value)] if note.type in {
                                    NoteType.LONG_ON,
                                    NoteType.LONG_OFF,
                                    NoteType.LONG_FLICK_LEFT,
                                    NoteType.LONG_FLICK_RIGHT,
                                }:
                                    # ロングアクト（ロングノート）／効果量ブースト

                                    skillpart_values[iskillpart][SkillValueIndices.BONUS_SCORE] = value

                                case _:
                                    LibsStageLogger.error("スコアボーナスのどれにも一致しませんでした。")

                        case EffectType.BONUS_COMBO:
                            # COMBOボーナス

                            match skillpart.value:
                                # 効果量

                                case float(value) if value >= 0.0:
                                    # COMBOボーナス／効果量ブースト
                                    # チューニング／効果量ブースト
                                    # キュートフォーカス、クールフォーカス、パッションフォーカス／効果量ブースト
                                    # オーバードライブ／効果量ブースト
                                    # オールラウンド／効果量ブースト
                                    # コーディネート／効果量ブースト
                                    # トリコロール・シナジー／効果量ブースト
                                    # トリコロール・スパイク（ライフを25消費して）／効果量ブースト

                                    skillpart_values[iskillpart][SkillValueIndices.BONUS_COMBO] = value

                                case float(value) if value < 0.0:
                                    # オルタネイト（20%ダウン）／ブースト無し

                                    skillpart_values[iskillpart][SkillValueIndices.BONUS_ALTERNATE1] = value

                                case str(LIFE):
                                    # ライフスパークル／効果量ブースト

                                    match LIFE:
                                        # 効果量を示す文字列

                                        case "ライフ値が多いほど":
                                            skillpart_values[iskillpart][SkillValueIndices.BONUS_COMBO] = (
                                                Simulator._lifesparkles.value(context.life.value)
                                            )
                                            LibsStageLogger.error("ライフスパークルのレア度をSSRとした（仮）。")

                                        case _:
                                            LibsStageLogger.error(f"ライフスパークルの不一致: {LIFE}")

                                case _:
                                    LibsStageLogger.error("COMBOボーナスのどれにも一致しませんでした。")

                        case EffectType.BOOST_SCORE:
                            # スコアブースト

                            match skillpart.value:
                                # 効果量

                                case float(value):
                                    # キュートアンサンブル（自分以外のキュートアイドルのスコアボーナス）
                                    # クールアンサンブル（自分以外のクールアイドルのスコアボーナス）
                                    # パッションアンサンブル（自分以外のパッションアイドルのスコアボーナス）
                                    # トリコロール・シンフォニー（自分以外のアイドルのスコアボーナス）
                                    # スターライトアンサンブル（自分以外のアイドルのスコアボーナス）

                                    skillpart_values[iskillpart][SkillValueIndices.BOOST_SCORE] = value

                                case str(DOMINANT):
                                    # ドミナント・ハーモニー（キュートアイドルのスコアボーナス）
                                    # ドミナント・ハーモニー（クールアイドルのスコアボーナス）
                                    # ドミナント・ハーモニー（パッションアイドルのスコアボーナス）

                                    match DOMINANT:
                                        # 効果量を示す文字列

                                        case "キュートアイドルの人数に応じて":
                                            number = context.number_typelist[0]

                                        case "クールアイドルの人数に応じて":
                                            number = context.number_typelist[1]

                                        case "パッションアイドルの人数に応じて":
                                            number = context.number_typelist[2]

                                        case _:
                                            LibsStageLogger.error(f"ドミナント・ハーモニーの不一致: {DOMINANT}")

                                    skillpart_values[iskillpart][SkillValueIndices.BOOST_SCORE] = (
                                        Simulator._dominants.value(number, 0)
                                    )
                                    LibsStageLogger.error(
                                        "ドミナント・ハーモニー／スコアボーナスは、ゲスト有りとした（仮）。"
                                    )

                                case _:
                                    LibsStageLogger.error("スコアブーストのどれにも一致しませんでした。")

                        case EffectType.BOOST_COMBO:
                            # COMBOブースト

                            match skillpart.value:
                                # 効果量

                                case float(value):
                                    # キュートアンサンブル（自分以外のキュートアイドルのCOMBOボーナス）
                                    # クールアンサンブル（自分以外のクールアイドルのCOMBOボーナス）
                                    # パッションアンサンブル（自分以外のパッションアイドルのCOMBOボーナス）
                                    # トリコロール・シンフォニー（自分以外のアイドルのCOMBOボーナス）
                                    # スターライトアンサンブル（自分以外のアイドルのCOMBOボーナス）

                                    skillpart_values[iskillpart][SkillValueIndices.BOOST_COMBO] = value

                                case str(DOMINANT):
                                    # ドミナント・ハーモニー（キュートアイドルのCOMBOボーナス）
                                    # ドミナント・ハーモニー（クールアイドルのCOMBOボーナス）
                                    # ドミナント・ハーモニー（パッションアイドルのCOMBOボーナス）

                                    match DOMINANT:
                                        # 効果量を示す文字列

                                        case "キュートアイドルの人数に応じて":
                                            number = context.number_typelist[0]

                                        case "クールアイドルの人数に応じて":
                                            number = context.number_typelist[1]

                                        case "パッションアイドルの人数に応じて":
                                            number = context.number_typelist[2]

                                        case _:
                                            LibsStageLogger.error(f"ドミナント・ハーモニーの不一致: {DOMINANT}")

                                    skillpart_values[iskillpart][SkillValueIndices.BOOST_COMBO] = (
                                        Simulator._dominants.value(number, 1)
                                    )
                                    LibsStageLogger.error(
                                        "ドミナント・ハーモニー／COMBOボーナスは、ゲスト有りとした（仮）。"
                                    )

                                case _:
                                    LibsStageLogger.error("COMBOブーストのどれにも一致しませんでした。")

                        case EffectType.BOOST_SKILL:
                            # 特技ブースト

                            match skillpart.value:
                                # 効果量

                                case float(value):
                                    # スキルブースト（自分以外のアイドルの特技ボーナス）

                                    skillpart_values[iskillpart][SkillValueIndices.BOOST_SCORE] = (
                                        value  # スコアブースト
                                    )
                                    skillpart_values[iskillpart][SkillValueIndices.BOOST_COMBO] = value  # COMBOブースト
                                    life_boost.append(value)
                                    LibsStageLogger.error("スキルブースト（ライフ回復量ブースト）は、未処理（仮）。")

                                case _:
                                    LibsStageLogger.error("特技ブーストのどれにも一致しませんでした。")

                        case EffectType.BOOST_OTHER_SKILL:
                            # 他特技ブースト
                            # トリコロール・シンフォニー（ライフ回復）
                            # トリコロール・シンフォニー（オーバードライブのライフ回復）
                            # トリコロール・シンフォニー（オールラウンドのライフ回復）
                            # トリコロール・シンフォニー（トリコロール・シナジーのライフ回復）
                            # トリコロール・シンフォニー（ダメージガードでライフ回復）
                            # トリコロール・シンフォニー（クリスタル・ヒールのライフ減少量ダウン）

                            match skillpart.value:
                                # 効果量
                                case float(value):
                                    life_boost.append(value)

                            LibsStageLogger.error("他特技ブーストは、未処理（仮）。")

                        case EffectType.ENCORE:
                            # アンコール

                            LibsStageLogger.error("アンコールは、未処理（仮）。")

                        case EffectType.COPY_BONUS_SCORE:
                            # スコアボーナスコピー
                            # リフレイン（LIVE中に発動した最も高いスコアアップ効果を適用）

                            skillpart_values[iskillpart][SkillValueIndices.BONUS_SCORE] = 0.18
                            LibsStageLogger.error("リフレイン・スコアボーナス（仮）")

                        case EffectType.COPY_BONUS_COMBO:
                            # COMBOボーナスコピー
                            # リフレイン（LIVE中に発動した最も高いCOMBOボーナス効果を適用）

                            skillpart_values[iskillpart][SkillValueIndices.BONUS_COMBO] = 0.18
                            LibsStageLogger.error("リフレイン・COMBOボーナス（仮）")

                        case EffectType.COPY_BOOST_SCORE:
                            # オルタネイト（LIVE中に発動した最も高いスコアアップ効果を極大アップして適用）

                            match skillpart.value:
                                # 効果量

                                case float(value):
                                    skillpart_values[iskillpart][SkillValueIndices.BONUS_ALTERNATE] = 0.18
                                    LibsStageLogger.error("オルタネイト・コピースコアボーナス（仮）")
                                    skillpart_values[iskillpart][SkillValueIndices.BOOST_ALTERNATE] = value

                                case _:
                                    LibsStageLogger.error("オルタネイトのどれにも一致しませんでした。")

                        case EffectType.COPY_BOOST_COMBO:
                            # ミューチャル（LIVE中に発動した最も高いCOMBOボーナス効果を極大アップして適用）

                            match skillpart.value:
                                # 効果量

                                case float(value):
                                    skillpart_values[iskillpart][SkillValueIndices.BONUS_MUTUAL] = 0.18
                                    LibsStageLogger.error("ミューチャル・コピーCOMBOアボーナス（仮）")
                                    skillpart_values[iskillpart][SkillValueIndices.BOOST_MUTUAL] = value

                                case _:
                                    LibsStageLogger.error("ミューチャルのどれにも一致しませんでした。")

                        case EffectType.MAGIC:
                            # シンデレラマジック（ユニット編成アイドル全員の特技効果を発動し、最も高い効果を適用）

                            skillpart_values[iskillpart][SkillValueIndices.BONUS_SCORE] = 0.18
                            skillpart_values[iskillpart][SkillValueIndices.BONUS_SCORE + 1] = 0.7
                            skillpart_values[iskillpart][SkillValueIndices.BONUS_COMBO] = 0.17
                            skillpart_values[iskillpart][SkillValueIndices.BOOST_COMBO] = 0.7
                            LibsStageLogger.error("シンデレラマジック・特技効果（仮）")
                            LibsStageLogger.error("シンデレラマジック・他特技効果（仮）")

                        case EffectType.ADD_LIFE:
                            # ライフ回復。

                            match skillpart.value:
                                # 効果量

                                case float(value):
                                    # ライフ回復／回復量ブースト
                                    # オーバードライブ／回復量ブースト
                                    # オールラウンド／回復量ブースト
                                    # トリコロール・シナジー／回復量ブースト

                                    life.append(int(value))

                        case EffectType.NO_DAMAGE:
                            # ダメージガード（ライフが減少しなくなる）
                            # 発動要件（ライフを**消費して）を対象、``ALL PERFECT`` だからノートは非対象。

                            life.append(0)
                            LibsStageLogger.error("ダメージガード（仮）")

                        case EffectType.DOWN_DAMAGE:
                            # クリスタル・ヒール（LIVE中のライフゲージ減少量を50%ダウンする。
                            # 発動要件（ライフを**消費して）を対象、``ALL PERFECT`` だからノートは非対象。

                            LibsStageLogger.error("クリスタル・ヒール（仮）")

                        case EffectType.ADD_LIFE_AT_START:
                            # クリスタル・ヒール（LIVE開始時にライフを200%まで回復）／ブースト無し

                            pass

                        case (
                            EffectType.NA
                            | EffectType.CONCENTRATION
                            | EffectType.SUPPORT_PERFECT
                            | EffectType.SUPPORT_COMBO
                        ):
                            # スコア計算に影響しない特技パーツ。
                            # CONCENTRATION: コンセントレーション（PERFECT判定される時間が短くなる）／ブースト無し
                            # SUPPORT_PERFECT: PERFECTサポート／判定強化ブースト
                            # SUPPORT_PERFECT: チューニング（**をPERFECTにする）／判定強化ブースト
                            # SUPPORT_COMBO: COMBOサポート／判定強化ブースト
                            # SUPPORT_COMBO: オーバーロード（**でもCOMBO継続）／判定強化ブースト
                            # SUPPORT_COMBO: オーバードライブ（PERFECTのみCOMBO継続）／ブースト無し

                            pass

                        case _:
                            # 特技パーツの抜け漏れ。

                            LibsStageLogger.error(
                                f"{self.__class__.__name__}._skill_values: {skill.name}/{skillpart.name}"
                            )

                    # 終端：特技パーツごと
                    LibsStageLogger.debug(f"    {iskillpart}, {skillpart_values[iskillpart]}")

                # 終端：メンバーごと＆特技発動
                LibsStageLogger.debug(f"  {position}人目, {list(map(abs_max, zip(*skillpart_values)))}")
                skill_values.append(list(map(abs_max, zip(*skillpart_values))))

        # 保留していたライフ回復を実施（ブースト未実装）。
        context.life.update(sum(life))

        result: list[float] = (
            list(map(sum, zip(*skill_values))) if context.on_resonance else list(map(abs_max, zip(*skill_values)))
        )
        LibsStageLogger.debug(f"{note.timestamp}/{result}/{context.life.value}")

        return result


if __name__ == "__main__":
    print(__file__)
