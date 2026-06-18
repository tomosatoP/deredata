"""
デレステの ``ユニットのアピール計算`` を扱うモジュール。

ライブのスコア計算前に、アピール（ボーカル・ダンス・ビジュアル・ライフ・特技発動率・継続期間）値を確定する。

まずは、通常のゲストメンバー有りの ``WIDEライブ`` のみ対応する。
``GrandLive`` や ``LiveCarnival（Booth効果）`` にも対応したい。

    .. csv-table:: 通常ライブとLiveCarnivalのライブの比較
        :header-rows: 1
        :stub-columns: 1

        "項目", "通常ライブ", "LiveCarnival"
        "サポートメンバー", "有り", "無し"
        "ゲスト", "有り", "無し"
        "ゲストサポート", "無し", "センター以外に1名配置可能。ライブ全体で3名まで配置可能"
        "マイスタイル", "？", "ユニットに1名配置可能"

    .. csv-table:: LiveCarnivalのBooth効果
        :header-rows: 1
        :stub-columns: 1
        :widths: 1, 3

        "BOOTH効果", "説明"
        "| キュート
        | クール
        | パッション", "対象タイプ楽曲のみ選択可能、対象タイプアイドルのアピール値アップ。"
        "全てのアイドル", "全アイドルのアピール値がアップ。"
        "| ボーカル
        | ダンス
        | ビジュアル", "対象アピール値がアップ。"
        "| ボーカルのみ
        | ダンスのみ
        | ビジュアルのみ", "対象アピール値がアップ、それ以外はゼロ。"
        "ユニットのライフ", "ユニットのライフに応じてアピール値がアップ。"
        "アイドルのスターランク", "アイドルのスターランクに応じてアピール値がアップ。"
        "プロデュースpt", "アイドルの開放されているプロデュースptに応じてアピール値がアップ。"
        "イベント指定アイドル", "イベント指定アイドルのアピール値アップ。"
        "選曲指定", "アピール値アップ。"
        "特技指定", "対象の特技を持つアイドルのみアピール値アップ。"

:入力:
    - デレステ譜面データ
    - ユニット

:出力:
    レゾナンスの適否

    ユニット情報（リスト）
        - 0: ゲストを含むユニットメンバーのエピソード名リスト
        - 1: ゲストを含むユニットメンバーのボーカルアピール値リスト
        - 2: ゲストを含むユニットメンバーのダンスアピール値リスト
        - 3: ゲストを含むユニットメンバーのビジュアルアピール値リスト
        - 4: ゲストを含むユニットメンバーのライフリスト
        - 5: ユニットメンバーの特技発動確率リスト
        - 6: ユニットメンバーの特技継続期間リスト

    サポートメンバー情報（リスト）
        - 0: サポートメンバーのエピソード名リスト
        - 1: サポートメンバーのボーカルアピール値リスト
        - 2: サポートメンバーのダンスアピール値リスト
        - 3: サポートメンバーのビジュアルアピール値リスト

:todo:
    - BOOTH効果の実装。
    - 関数 breakdown2buffparts と buffwrap の統合。
    - センター効果・ワールドレべルの実装。
    - 楽曲タイプ一致の実装修正：シンデレラブレスから他のセンター効果を呼び出し時の対応。
"""

import numpy as np
from enum import IntEnum
from typing import Any, Callable
from functools import singledispatch
from dataclasses import dataclass, field
from functools import wraps, partial

from deredata.libs.database.musics import SongType, Music
from deredata.libs.database.enumerations import IdolType, DominantType, MusicType, UnitType
from deredata.libs.database.idols import Idol, Idols
from deredata.libs.database.episodes import Episode, Episodes
from deredata.libs.database.units import Unit
from deredata.libs.database.buffs import BuffPart, Buff, Buffs, AppealType
from deredata.libs.database.skills import Skills, duration_value, probability_value
from deredata.libs.database.potentials import Potentials

from kivy.logger import Logger as LibsBackstageLogger


class BackstageError(Exception):
    """backstageモジュールのエラーハンドラ。"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsBackstageLogger.error(f"BackstageError: {args}")


class AppealIndices(IntEnum):
    """
    エピソード名を除くアピールタイプの列挙クラス。ボーナス配列の添え字に相当する。

    :VOCAL: 0: ボーカル
    :DANCE: 1: ダンス
    :VISUAL: 2: ビジュアル
    :LIFE: 3: ライフ
    :PROBABILITY: 4: 特技発動率
    :DURATION: 5: 特技継続期間
    """

    VOCAL = 0
    DANCE = 1
    VISUAL = 2
    LIFE = 3
    PROBABILITY = 4
    DURATION = 5


class BoothIndices(IntEnum):
    """
    BOOTH効果の列挙クラス。ブース効果の添え字に相当する。

    :NA 0: 非該当
    :ALL 1: 全てのアイドルのアピール値アップ。
    :CUTE 2: キュートタイプ楽曲のみ選択可能、キュートタイプアイドルのアピール値アップ。
    :COOL 3: クールタイプ楽曲のみ選択可能、クールタイプアイドルのアピール値アップ。
    :PASSION 4: パッションタイプ楽曲のみ選択可能、パッションタイプアイドルのアピール値アップ。
    :SELECTED 5: 特定楽曲のみ選択可能、アピール値アップ。
    :VOCAL 9: ボーカルアピール値がアップ。
    :DANCE 10: ダンスアピール値がアップ。
    :VISUAL 11: ビジュアルアピール値がアップ。
    :VOCAL_ONLY 12: ボーカルアピール値のみアップ、ダンス、ビジュアルアピール値は ZERO。
    :DANCE_ONLY 13: ダンスアピール値のみアップ、ボーカル、ビジュアルアピール値は ZERO。
    :VISUAL_ONLY 14: ビジュアルアピール値のみアップ、ボーカル、ダンスアピール値は ZERO。
    :LIFE 15: ユニットのライフに応じてアピール値がアップ。
    :STAR_RANK 16: アイドルのスターランクに応じてアピール値がアップ。
    :PRODUCE_PT 17: アイドルの開放されているプロデュースptに応じてアピール値がアップ。
    :EVENT_IDOL 18: イベント指定アイドルのアピール値アップ。
    :SKILL 19: 対象の特技を持つアイドルのみアピール値アップ。
    """

    NA = 0
    CUTE = 1
    COOL = 2
    PASSION = 3
    ALL = 4
    CUTE_SELECTED = 5
    COOL_SELECTED = 6
    PASSION_SELECTED = 7
    ALL_SELECTED = 8
    VOCAL = 9
    DANCE = 10
    VISUAL = 11
    VOCAL_ONLY = 12
    DANCE_ONLY = 13
    VISUAL_ONLY = 14
    LIFE = 15
    STAR_RANK = 16
    PRODUCE_PT = 17
    EVENT_IDOL = 18
    SKILL = 19


@dataclass
class BoothEffect:
    """
    BOOTH効果のデータクラス（まだ中身無し）。
    """

    pass


@dataclass
class BuffPartContext:
    """
    センター効果パーツのコンテキストのデータクラス。

    アピールのボーナス配列を取得する際、必要となるセンター効果パーツに関わる各種条件を格納する。

    :アピール: ボーカル、ダンス、ビジュアル、ライフ、特技発動確率、特技継続期間

    :param BuffPart buffpart: センター効果パーツ。
    :param SongType live_songtype: ライブの楽曲タイプ。
    :param list[IdolType] idoltypes_list: ゲストを含むユニットメンバーのアイドルタイプリスト
    :param list[DominantType] dominanttypes_list: ゲストを含むユニットメンバーのドミナントアイドルタイプリスト
    """

    buffpart: BuffPart = BuffPart()
    live_songtype: SongType = SongType.ALL
    idoltypes_list: list[IdolType] = field(default_factory=list)
    dominanttypes_list: list[DominantType] = field(default_factory=list)


@dataclass
class BuffContext:
    """
    センター効果のコンテキストのデータクラス。

    アピールのボーナス配列を取得する際、必要となるセンター効果に関わるの各種条件を格納する。

    :アピール: ボーカル、ダンス、ビジュアル、ライフ、特技発動確率、特技継続期間

    :param bool on_resonance: レゾナンス（全ての特技効果が重複時に加算）
    :param int position: 立ち位置（センター、左隣、右隣、左端、右端、ゲスト）
    :param Buff buff: センター効果
    :param SongType live_songtype: ライブの楽曲のタイプ
    :param set[IdolType] idoltypes_set: ゲストを含むユニットメンバーのアイドルタイプ集合
    :param set[DominantType] dominanttypes_set: ゲストを含むユニットメンバーのドミナントアイドルタイプ集合
    :param set[str] skillclasses_set: ゲストを含むユニットメンバーの特技集合
    :param list[IdolType] idoltypes_list: ゲストを含むユニットメンバーのアイドルタイプリスト
    :param list[DominantType] dominanttypes_list: ゲストを含むユニットメンバーのドミナントアイドルタイプリスト
    :param list[Episode] episodes_list: ゲストを含むユニットメンバーのエピソードリスト
    :param list[Buff] buffs_list: ゲストを含むユニットメンバーのセンター効果リスト
    """

    on_resonance: bool = False
    position: int = 0
    buff: Buff = Buff()
    live_songtype: SongType = SongType.ALL
    idoltypes_set: set[IdolType] = field(default_factory=set)
    dominanttypes_set: set[DominantType] = field(default_factory=set)
    skillclasses_set: set[str] = field(default_factory=set)
    idoltypes_list: list[IdolType] = field(default_factory=list)
    dominanttypes_list: list[DominantType] = field(default_factory=list)
    episodes_list: list[Episode] = field(default_factory=list)
    buffs_list: list[Buff] = field(default_factory=list)


def appeal_formula(bonuses: list[np.ndarray], booth_buff: BoothIndices = BoothIndices.NA) -> np.ndarray:
    """
    アピールを計算する。

    ボーナス値を要素とするNUMPY配列（軸0: 効果、軸1: アピール、軸2: メンバー）から、
    **効果** を組み合わせてアピール（軸0: アピール、軸1: メンバー）を求める。

        計算式: :math:`(bonuses[0]+bonuses[1])\\times(1.00+\\displaystyle \\sum{bonuses[2:]})`

    ボーカル・ダンス・ビジュアル
        小数点以下切り上げ。
        GrandLiveでは、ユニット単位で適用し、合計する。

            ユニットメンバーの場合
                - bonuses[0]: 基礎値のボーナス配列
                - bonuses[1]: ポテンシャル補正のボーナス配列
                - bonuses[2]: 楽曲タイプ一致効果のボーナス配列
                - bonuses[3]: ルーム効果のボーナス配列
                - bonuses[4]: センター効果のボーナス配列
                - bonuses[5]: ゲストのセンター効果のボーナス配列（ゲストを含まない場合は、ZERO で埋める）
                - bonuses[6]: BOOTH効果

            サポートメンバーの場合（**0.5倍する**）
                - bonuses[0]: 基礎値のボーナス配列
                - bonuses[1]: ポテンシャル補正のボーナス配列
                - bonuses[2]: 楽曲タイプ一致効果のボーナス配列

    ライフ
        小数点以下切り上げ。
        サポートメンバーには、適用しない。
        GrandLiveでは、ユニット単位で適用し、平均値を採用する。

                - bonuses[0]: 基礎値のボーナス配列
                - bonuses[1]: ポテンシャル補正のボーナス配列
                - bonuses[2]: センター効果のボーナス配列
                - bonuses[3]: ゲストのセンター効果のボーナス配列（ゲストを含まない場合は、ZERO で埋める）

    特技発動確率
        サポートメンバーには、適用しない。

                - bonuses[0]: :math:`基礎値\\times(1.00+\\dfrac{特技LV-1}{18})`
                - bonuses[1]: ポテンシャル補正のボーナス配列
                - bonuses[2]: 楽曲タイプ一致効果のボーナス配列
                - bonuses[3]: センター効果のボーナス配列
                - bonuses[4]: ゲストのセンター効果のボーナス配列（ゲストを含まない場合は、ZERO で埋める）


    特技継続時間
        サポートメンバーには、適用しない。

                - bonuses[0]: :math:`基礎値\\times(1.00+\\dfrac{特技LV-1}{18})`

    :param list[np.ndarray] bonuses: 要素がボーナス値の配列のリスト。

    :return: アピール。
    :rtype: np.ndarray
    """

    return (bonuses[0] + bonuses[1]) * (1.0 + sum(bonuses[2:]))


@singledispatch
def ismatch(type: Any, member: IdolType | DominantType) -> bool:
    """
    タイプの一致を判定する。

    *type* 引数と *member* 引数のタイプが一致する場合に、``True`` を返す。
    それ以外は、 ``False`` を返す。

    :param Any type: 適用楽曲タイプ（SongType）／適用アイドルタイプ（IdolType）。
    :param IdolType|DominantType member: 適用メンバーのアイドルタイプ／ドミナントアイドルタイプ。

    :return: タイプが一致する時は **True** 、一致しない時は **False** を返す。
    :rtype: bool
    """

    LibsBackstageLogger.error(f"backstage.ismatch: {type}が、不正です。")
    return False


@ismatch.register(SongType)
def _(type: SongType, member: IdolType | DominantType) -> bool:
    """
    タイプ一致（SongType）。
    """

    match [type, member]:
        case [SongType.ALL, x]:  # noqa: F841
            return True

        case [SongType(stype), IdolType(idol)]:
            return True if stype.name == idol.name else False

        case [SongType(stype), DominantType(dominant)]:
            return True if stype.name == dominant.name else False

        case _:
            LibsBackstageLogger.error("backstage.ismatch: 楽曲タイプが、一致しませんでした。")
            return False


@ismatch.register(IdolType)
def _(type: IdolType, member: IdolType | DominantType) -> bool:
    """
    タイプ一致（IdolType）。
    """

    match [type, member]:
        case [IdolType.UNIT, x]:  # noqa: F841
            return True

        case [IdolType(itype), IdolType(idol)]:
            return True if itype == idol else False

        case [IdolType(itype), DominantType(dominant)]:
            return True if itype.name == dominant.name else False

        case _:
            LibsBackstageLogger.error("backstage.ismatch: アイドルタイプが、一致しませんでした。")
            return False


def buffpartwrap(func: Callable) -> Callable:
    """
    センター効果パーツのボーナス配列を返すラッパー関数。

    :ボーナス配列:
        ボーナスを要素とする二次元NUMPY配列。
            - 軸0: アピールタイプ
            - 軸1: ユニットメンバーの立ち位置
    :前処理:
        デバッグ用ログを出力する。
    :後処理:
        | ボーナス配列を初期化する。
        | ボーナス配列に対して、指定（戻り値）のアピールタイプのボーナスを更新する。

    :param Callable func: センター効果パーツのAppealIndicesリストを返す関数。

    :return: ラッパー関数
    :rtype: Callable
    """

    @wraps(func)
    def wrapper(context: BuffPartContext) -> np.ndarray:
        """
        センター効果パーツのアピールタイプのリストを返す。
        ラッパー関数により、センター効果パーツのボーナス配列に変換される。

        :param BuffPartContext context: センター効果パーツのコンテキスト。

        :return: アピールタイプのリスト。
        :rtype: list[AppealIndices]
        """

        # 前処理
        LibsBackstageLogger.debug(f"backstage.buffpartwrap: センター効果パーツ・{context.buffpart.name}を処理。")

        appealidices: list[AppealIndices] = partial(func, context)()

        # 後処理
        bonus: float = context.buffpart.value
        member: IdolType = context.buffpart.member
        idoltypes: list[IdolType] = context.idoltypes_list
        dominanttypes: list[DominantType] = context.dominanttypes_list

        bonus_array: np.ndarray = np.zeros((len(AppealIndices), len(context.idoltypes_list)))
        for id in appealidices:
            if not dominanttypes:
                bonus_array[id] = np.array([bonus if ismatch(member, type) else 0.0 for type in idoltypes])
            else:
                bonus_array[id] = np.maximum(
                    np.array([bonus if ismatch(member, type) else 0.0 for type in idoltypes]),
                    np.array([bonus if ismatch(member, type) else 0.0 for type in dominanttypes]),
                )

        return bonus_array

    return wrapper


@buffpartwrap
def buffpart_all(context: BuffPartContext) -> list[AppealIndices]:
    """
    センター効果パーツ・全アピール（ボーカル、ダンス、ビジュアル）タイプのリストを返す。

    ラッパー関数により、センター効果パーツのボーナス配列に変換される。

    :param BuffPartContext context: センター効果パーツ・全アピールのコンテキスト。

    :return: アピールタイプのリスト。
    :rtype: list[AppealIndices]
    """

    match context.buffpart.music:
        # 適用楽曲

        case MusicType.NA:
            pass

        case MusicType.ALL if context.live_songtype == SongType.ALL:
            pass

        case MusicType.CUTE if context.live_songtype == SongType.CUTE:
            pass

        case MusicType.COOL if context.live_songtype == SongType.COOL:
            pass

        case MusicType.PASSION if context.live_songtype == SongType.PASSION:
            pass

        case _:
            LibsBackstageLogger.error(f"backstage.buffpart_all: この楽曲では、{context.buffpart.name} を適用できない。")
            return []

    return [AppealIndices.VOCAL, AppealIndices.DANCE, AppealIndices.VISUAL]


@buffpartwrap
def buffpart_vocal(context: BuffPartContext) -> list[AppealIndices]:
    """
    センター効果パーツ・ボーカルタイプのリストを返す。

    ラッパー関数により、センター効果パーツのボーナス配列に変換される。

    :param BuffPartContext context: センター効果パーツ・ボーカルのコンテキスト。

    :return: アピールタイプのリスト。
    :rtype: list[AppealIndices]
    """

    return [AppealIndices.VOCAL]


@buffpartwrap
def buffpart_dance(context: BuffPartContext) -> list[AppealIndices]:
    """
    センター効果パーツ・ダンスタイプのリストを返す。

    ラッパー関数により、センター効果パーツのボーナス配列に変換される。

    :param BuffPartContext context: センター効果パーツ・ダンスのコンテキスト。

    :return: アピールタイプのリスト。
    :rtype: list[AppealIndices]

    :todo: ワールドレベル（自分のダンスアピール値100%アップ、フェイスオープンしたら全員のダンスアピール値130%アップ）
    """

    LibsBackstageLogger.error("backstage.buffpart_dance: センター効果・ワールドレベルのヘレン対応は、実装中です。")
    LibsBackstageLogger.error(
        "backstage.buffpart_dance: センター効果・ワールドレベルのフェイスオープン対応は、未実装です。"
    )
    return [AppealIndices.DANCE]


@buffpartwrap
def buffpart_visual(context: BuffPartContext) -> list[AppealIndices]:
    """
    センター効果パーツ・ビジュアルタイプのリストを返す。

    ラッパー関数により、センター効果パーツのボーナス配列に変換される。

    :param BuffPartContext context: センター効果パーツ・ビジュアルのコンテキスト。

    :return: アピールタイプのリスト。
    :rtype: list[AppealIndices]
    """

    return [AppealIndices.VISUAL]


@buffpartwrap
def buffpart_life(context: BuffPartContext) -> list[AppealIndices]:
    """
    センター効果パーツ・ライフアピールのリストを返す。

    ラッパー関数により、センター効果パーツのボーナス配列に変換される。

    :param BuffPartContext context: センター効果パーツ・ライフのコンテキスト。

    :return: アピールタイプのリスト。
    :rtype: list[AppealIndices]
    """

    return [AppealIndices.LIFE]


@buffpartwrap
def buffpart_probability(context: BuffPartContext) -> list[AppealIndices]:
    """
    センター効果パーツ・特技発動確率アピールのリストを返す。

    ラッパー関数により、センター効果パーツのボーナス配列に変換される。

    :param BuffPartContext context: センター効果パーツ・特技発動確率のコンテキスト。

    :return: アピールタイプのリスト。
    :rtype: list[AppealIndices]
    """

    return [AppealIndices.PROBABILITY]


def breakdown2buffparts(buffcontext: BuffContext, bonus_array_ext: np.ndarray) -> np.ndarray:
    """
    ``拡大ボーナス配列`` を更新する。
    
    センター効果（buffcontext.buff）のセンター効果パーツに対応するセンター効果パーツ関数を呼び出し、\
    戻り値の ``ボーナス配列`` で ``拡大ボーナス配列`` を更新する。

    :param BuffContext buffcontext: センター効果コンテキスト。
    :param np.ndarray bonus_array_ext: 初期化済みのセンター効果の ``拡大ボーナス配列`` 。

    :return: センター効果の ``拡大ボーナス配列`` 。
    :rtype: np.ndarray

    :todo: この関数は ``buffwrap`` に組み込む。
    """

    contexts: list[BuffPartContext] = list()
    if buffcontext.buff.buff in [
        "ドミナント・デュエット（ボイス＆ステップ）",
        "ドミナント・デュエット（ステップ＆メイク）",
        "ドミナント・デュエット（メイク＆ボイス）",
    ]:
        for buffpart in list(buffcontext.buff.buffparts):
            if buffpart.appeal in appeal_funcname:
                contexts.append(
                    BuffPartContext(
                        buffpart,
                        buffcontext.live_songtype,
                        buffcontext.idoltypes_list,
                        buffcontext.dominanttypes_list,
                    )
                )
    else:
        for buffpart in list(buffcontext.buff.buffparts):
            if buffpart.appeal in appeal_funcname:
                contexts.append(
                    BuffPartContext(
                        buffpart,
                        buffcontext.live_songtype,
                        buffcontext.idoltypes_list,
                    )
                )

    for i, context in enumerate(contexts):
        if context.buffpart.appeal in appeal_funcname:
            bonus_array_ext[i] = appeal_funcname[context.buffpart.appeal](context)
        else:
            LibsBackstageLogger.error(f"backstage.breakdown2buffparts: {context.buffpart.appeal}は、未実装です。")

    return bonus_array_ext


def buffwrap(func: Callable) -> Callable:
    """
    センター効果のボーナス配列を返すラッパー関数。

    :ボーナス配列:
        ボーナスを要素とする二次元NUMPY配列。
            - 軸0: アピールタイプ
            - 軸1: ユニットメンバーの立ち位置
    :拡大ボーナス配列:
        ボーナスを要素とする三次元NUMPY配列。
            - 軸0: センター効果パーツ
            - 軸1: アピールタイプ
            - 軸2: ユニットメンバー立ち位置
    :前処理:
        | デバッグ用ログを出力する。
        | 拡大ボーナス配列を初期化する。
    :後処理:
        拡大ボーナス配列からボーナス配列に変換する。

    :param Callable func: センター効果のボーナス配列を返す関数。

    :return: ラッパー関数
    :rtype: Callable
    """

    @wraps(func)
    def wrapper(context: BuffContext) -> np.ndarray:
        """
        センター効果の拡大ボーナス配列を返す。

        ラッパー関数により、センター効果のボーナス配列に変換される。

        :param BuffContext context: コンテキスト。
        :param np.ndarray bonus_array_ext: 初期化済みの拡大ボーナス配列。

        :return: センター効果の拡大ボーナス配列。
        :rtype: np.ndarray
        """

        # 大きい方（片方がZEROの時は、もう片方）を返すnumpy.ufunc定義
        abs_max = np.frompyfunc(lambda x, y: max(x, y) if max(x, y) != 0.0 else min(x, y), 2, 1)

        # 前処理
        LibsBackstageLogger.debug(f"backstage.buffwrap: センター効果・{context.buff.buff}を処理。")
        bonus_array_ext = np.zeros((len(context.buff.buffparts), len(AppealIndices), len(context.episodes_list)))

        result = partial(func, context, bonus_array_ext)()

        return abs_max.reduce(result[:], axis=0).astype(float)

    return wrapper


@buffwrap
def buff_cinderella_bless(context: BuffContext, bonus_array_ext: np.ndarray) -> np.ndarray:
    """
    シンデレラブレス系センター効果の拡大ボーナス配列を返す。

    ラッパー関数により、センター効果のボーナス配列に変換される。

    対象センター効果
        シンデレラブレス。
            ゲストを含むユニット編成アイドル全員のセンター効果を発揮し、最も高い効果を適用。

    :param BuffContext context: センター効果のコンテキスト。
    :param np.ndarray bonus_array_ext: 初期化済みのセンター効果の拡大ボーナス配列。

    :return: センター効果の拡大ボーナス配列
    :rtype: np.ndarray
    """

    match context.position:
        # 立ち位置

        case 0 | 5:
            # センターもしくはゲストのセンター効果：シンデレラブレス。

            temp = np.zeros((len(context.episodes_list), len(AppealIndices), len(context.episodes_list)))

            for member, episode in enumerate(context.episodes_list):
                if member != context.position or episode.buff_class != "シンデレラブレス":
                    LibsBackstageLogger.debug(
                        f"backstage.buff_cinderella_bless: シンデレラブレス[{context.position}]  {member}人目"
                    )

                    if episode.buff_class in buff_funcname:
                        # アピール値の計算に必要、かつ実装済みのセンター効果

                        temp[member] = buff_funcname[episode.buff_class](
                            BuffContext(
                                position=member,
                                buff=Calculator._buffs.get(context.episodes_list[member].buff),
                                live_songtype=context.live_songtype,
                                idoltypes_set=context.idoltypes_set,
                                dominanttypes_set=context.dominanttypes_set,
                                skillclasses_set=context.skillclasses_set,
                                idoltypes_list=context.idoltypes_list,
                                dominanttypes_list=context.dominanttypes_list,
                                episodes_list=context.episodes_list,
                                buffs_list=context.buffs_list,
                            )
                        )

                    else:
                        LibsBackstageLogger.error(
                            f"backstage.buff_cinderella_bless: {episode.buff_class}は、未実装です。"
                        )
                        temp[member] = np.zeros((len(AppealIndices), len(context.episodes_list)))

            bonus_array_ext[0] = temp.max(axis=0)

        case _:
            # 以外（効果がセンターもしくはゲストと重複するだけなので、何もしない）。
            LibsBackstageLogger.debug(
                "appeal.buff_cinderella_bless: センター、ゲストではないため、シンデレラブレスは無効です。"
            )

    return bonus_array_ext


@buffwrap
def buff_multi_appeal(context: BuffContext, bonus_array_ext: np.ndarray) -> np.ndarray:
    """
    全アピール系センター効果の拡大ボーナス配列を返す。

    ラッパー関数により、センター効果のボーナス配列に変換される。

    対象センター効果
        キュートブリリアンス、クールブリリアンス、パッションブリリアンス。
            __アイドルの全アピール値__%アップ。

        キュートユニゾン、クールユニゾン、パッションユニゾン。
            __アイドルの全アピール値__%アップ、__楽曲なら__%アップ。

        キュートプリンセス、クールプリンセス、パッションプリンセス。
            __アイドルのみ編成時、全員の全アピール値__%アップ

        トリコロール・ユニゾン。
            3タイプ全てのアイドル編成時、全員の全アピール値__%アップ、全タイプ楽曲なら__%アップ。

    :param BuffContext context: センター効果のコンテキスト。
    :param np.ndarray bonus_array_ext: 初期化済みのセンター効果の拡大ボーナス配列。

    :return: センター効果の拡大ボーナス配列
    :rtype: np.ndarray
    """

    match context.buff.formation:
        case UnitType.NA:
            # キュートブリリアンス、クールブリリアンス、パッションブリリアンス。
            # キュート・ユニゾン、クール・ユニゾン、パッション・ユニゾン。
            pass

        case UnitType.ONLY_CUTE if context.idoltypes_set == {IdolType.CUTE}:
            # キュートプリンセス（キュートアイドルのみ編成時）
            pass

        case UnitType.ONLY_COOL if context.idoltypes_set == {IdolType.COOL}:
            # クールプリンセス（クールアイドルのみ編成時）
            pass

        case UnitType.ONLY_PASSION if context.idoltypes_set == {IdolType.PASSION}:
            # パッションプリンセス（パッションアイドルのみ編成時）
            pass

        case UnitType.ALL if context.idoltypes_set == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・ユニゾン（3タイプ全てのアイドル編成時）
            pass

        case _:
            LibsBackstageLogger.error("backstage.buff_multi_appeal: 編成要件を満たしていない。")
            return bonus_array_ext

    return breakdown2buffparts(context, bonus_array_ext)


@buffwrap
def buff_single_appeal(context: BuffContext, bonus_array_ext: np.ndarray) -> np.ndarray:
    """
    ボイス、ダンス、ビジュアル系センター効果の拡大ボーナス配列を返す。

    ラッパー関数により、センター効果のボーナス配列に変換される。

    対象センター効果
        キュートボイス、キュートステップ、キュートメイク。
            キュートアイドルの__アピール値__%アップ。

        クールボイス、クールステップ、クールメイク。
            クールアイドルの__アピール値__%アップ。

        パッションボイス、パッションステップ、パッションメイク。
            パッションアイドルの__アピール値__%アップ。

        シャイニーボイス、シャイニー・ステップ。
            全員の__アピール値__%アップ。

        トリコロール・ボイス、トリコロール・ステップ、トリコロール・メイク。
            3タイプ全てのアイドル編成時、全員の__アピール値__%アップ。

    :param BuffContext context: センター効果コンテキスト。
    :param np.ndarray bonus_array_ext: 初期化済みのセンター効果の拡大ボーナス配列。

    :return: センター効果の拡大ボーナス配列。
    :rtype: np.ndarray
    """

    match context.buff.formation:
        case UnitType.NA:
            # キュートボイス、キュートステップ、キュートメイク
            # クールボイス、クールステップ、クールメイク
            # パッションボイス、パッションステップ、パッションメイク
            # シャイニーボイス、シャイニー・ステップ

            pass

        case UnitType.ALL if context.idoltypes_set == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・ボイス、トリコロール・ステップ、トリコロール・メイク（3タイプ全てのアイドル編成時）

            pass

        case _:
            LibsBackstageLogger.error("backstage.buff_single_appeal: 編成要件を満たしていない。")
            return bonus_array_ext

    return breakdown2buffparts(context, bonus_array_ext)


@buffwrap
def buff_life(context: BuffContext, bonus_array_ext: np.ndarray) -> np.ndarray:
    """
    ライフ値系センター効果の拡大ボーナス配列を返す。

    ラッパー関数により、センター効果のボーナス配列に変換される。

    対象センター効果
        キュートエナジー、クールエナジー、パッションエナジー。
            __アイドルのライフ__%アップ

        キュートチアー、クールチアー、パッションチアー。
            __アイドルのみ編成時、全員のライフ__%アップ

    :param BuffContext context: センター効果のコンテキスト。
    :param np.ndarray bonus_array_ext: 初期化済みのセンター効果の拡大ボーナス配列。

    :return: センター効果の拡大ボーナス配列。
    :rtype: np.ndarray
    """

    match context.buff.formation:
        case UnitType.NA:
            # キュートエナジー、クールエナジー、パッションエナジー

            pass

        case UnitType.ONLY_CUTE if context.idoltypes_set == {IdolType.CUTE}:
            # キュートチアー（キュートアイドルのみ編成時）

            pass

        case UnitType.ONLY_COOL if context.idoltypes_set == {IdolType.COOL}:
            # クールチアー（クールアイドルのみ編成時）

            pass
        case UnitType.ONLY_PASSION if context.idoltypes_set == {IdolType.PASSION}:
            # パッションチアー（パッションアイドルのみ編成時）

            pass

        case _:
            LibsBackstageLogger.error("backstage.buff_life: 編成要件を満たしていない。")
            return bonus_array_ext

    return breakdown2buffparts(context, bonus_array_ext)


@buffwrap
def buff_probability(context: BuffContext, bonus_array_ext: np.ndarray) -> np.ndarray:
    """
    特技発動確率系センター効果の拡大ボーナス配列を返す。

    ラッパー関数により、センター効果のボーナス配列に変換される。

    対象センター効果
        キュートアビリティ、クールアビリティ、パッションアビリティ。
            __アイドルの特技発動確率__%アップ。

        トリコロール・アビリティ。
            3タイプ全てのアイドル編成時、全員の特技発動確率__%アップ。

    :param BuffContext context: センター効果のコンテキスト。
    :param np.ndarray bonus_array_ext: 初期化済みのセンター効果の拡大ボーナス配列。

    :return: センター効果の拡大ボーナス配列。
    :rtype: np.ndarray
    """

    match context.buff.formation:
        case UnitType.NA:
            # キュートアビリティ、クールアビリティ、パッションアビリティ

            pass

        case UnitType.ALL if context.idoltypes_set == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・アビリティ（3タイプ全てのアイドル編成時）

            pass

        case _:
            LibsBackstageLogger.error("backstage.buff_probability: 編成要件を満たしていない。")
            return bonus_array_ext

    return breakdown2buffparts(context, bonus_array_ext)


@buffwrap
def buff_resonance(context: BuffContext, bonus_array_ext: np.ndarray) -> np.ndarray:
    """
    レゾナンス系センター効果の拡大ボーナス配列を返す。

    ラッパー関数により、センター効果のボーナス配列に変換される。

    対象センター効果
        レゾナンス・ボイス、レゾナンス・ステップ、レゾナンス・メイク。
            5種類の特技編成時、__以外のアピール値を100%ダウンし、全ての特技効果が重複時に加算。

    :param BuffContext context: センター効果のコンテキスト。
    :param np.ndarray bonus_array_ext: 初期化済みのセンター効果の拡大ボーナス配列。

    :return: センター効果の拡大ボーナス配列。
    :rtype: np.ndarray
    """

    if len(context.skillclasses_set) >= 5:  # 5種類の特技編成時
        context.on_resonance = True  # 全ての特技効果が重複時に加算

    else:
        LibsBackstageLogger.error("backstage.buff_resonance: 特技が5種類未満のため、レゾナンスは発動しない。")
        return bonus_array_ext

    return breakdown2buffparts(context, bonus_array_ext)


@buffwrap
def buff_cross(context: BuffContext, bonus_array_ext: np.ndarray) -> np.ndarray:
    """
    クロス系センター効果の拡大ボーナス配列を返す。

    ラッパー関数により、センター効果のボーナス配列に変換される。

    対象センター効果
        キュート・クロス・クール。
            キュートとクールのアイドル編成時、全員の全アピール値__%アップ、獲得ファン数が__%アップ。
        キュート・クロス・パッション。
            キュートとパッションのアイドル編成時、全員の全アピール値__%アップ、獲得ファン数が__%アップ。

        クール・クロス・キュート。
            クールとキュートのアイドル編成時、全員の全アピール値__%アップ、全員の特技発動率__%アップ。
        クール・クロス・パッション。
            クールとパッションのアイドル編成時、全員の全アピール値__%アップ、全員の特技発動率__%アップ。

        パッション・クロス・キュート。
            パッションとキュートのアイドル編成時、全員の全アピール値__%アップ、全員のライフ__%アップ。
        パッション・クロス・クール。
            パッションとクールのアイドル編成時、全員の全アピール値__%アップ、全員のライフ__%アップ。

    :param BuffContext context: センター効果のコンテキスト。
    :param np.ndarray bonus_array_ext: 初期化済みのセンター効果の拡大ボーナス配列。

    :return: センター効果の拡大ボーナス配列。
    :rtype: np.ndarray
    """

    match context.buff.formation:
        case UnitType.CUTE_AND_COOL | UnitType.COOL_AND_CUTE if context.idoltypes_set >= {
            IdolType.CUTE,
            IdolType.COOL,
        }:
            pass

        case UnitType.COOL_AND_PASSION | UnitType.PASSION_AND_COOL if context.idoltypes_set >= {
            IdolType.COOL,
            IdolType.PASSION,
        }:
            pass

        case UnitType.PASSION_AND_CUTE | UnitType.CUTE_AND_PASSION if context.idoltypes_set >= {
            IdolType.PASSION,
            IdolType.CUTE,
        }:
            pass

        case _:
            LibsBackstageLogger.error("backstage.buff_cross: 編成要件を満たしていない。")
            return bonus_array_ext

    return breakdown2buffparts(context, bonus_array_ext)


@buffwrap
def buff_duet(context: BuffContext, bonus_array_ext: np.ndarray) -> np.ndarray:
    """
    デュエット系センター効果。

    ラッパー関数により、センター効果のボーナス配列に変換される。

    対象センター効果
        | キュート・デュエット（ボイス＆ステップ）。
        | クール・デュエット（ボイス＆ステップ）。
        | パッション・デュエット（ボイス＆ステップ）。

            __アイドルのみ編成時、__楽曲で全員のダンス＆ビジュアルアピール値__%アップ。

        | キュート・デュエット（ステップ＆メイク）。
        | クール・デュエット（ステップ＆メイク）。
        | パッション・デュエット（ステップ＆メイク）。

            __アイドルのみ編成時、__楽曲で全員のビジュアル＆ボーカルアピール値__%アップ。

        | キュート・デュエット（メイク＆ボイス）。
        | クール・デュエット（メイク＆ボイス）。
        | パッション・デュエット（メイク＆ボイス）。

            __アイドルのみ編成時、__楽曲で全員のボーカル＆ダンスアピール値__%アップ。

    :param BuffContext context: センター効果のコンテキスト。
    :param np.ndarray bonus_array_ext: 初期化済みのセンター効果の拡大ボーナス配列。

    :return: センター効果の拡大ボーナス配列。
    :rtype: np.ndarray
    """

    match [context.buff.formation, context.buff.music]:
        case [UnitType.ONLY_CUTE, SongType.CUTE] if (
            context.idoltypes_set == {IdolType.CUTE} and context.live_songtype == SongType.CUTE
        ):
            pass

        case [UnitType.ONLY_COOL, SongType.COOL] if (
            context.idoltypes_set == {IdolType.COOL} and context.live_songtype == SongType.COOL
        ):
            pass

        case [UnitType.ONLY_PASSION, SongType.PASSION] if (
            context.idoltypes_set == {IdolType.PASSION} and context.live_songtype == SongType.PASSION
        ):
            pass

        case _:
            LibsBackstageLogger.error("backstage.buff_duet: 編成要件もしくは楽曲要件を満たしていない。")
            return bonus_array_ext

    return breakdown2buffparts(context, bonus_array_ext)


@buffwrap
def buff_dominant_duet(context: BuffContext, bonus_array_ext: np.ndarray) -> np.ndarray:
    """
    ドミナント・デュエット系センター効果の拡大ボーナス配列を返す。

    ラッパー関数により、センター効果のボーナス配列に変換される。

    対象センター効果
        | ドミナント・デュエット（ボイス＆ステップ）。
        | ドミナント・デュエット（ステップ＆メイク）。
        | ドミナント・デュエット（メイク＆ボイス）。

            __楽曲で__アイドルにタイプボーナスが発生し__アピール値150%アップ、__アイドルの__アピール値160%アップ。

    :param BuffContext context: センター効果のコンテキスト。
    :param np.ndarray bonus_array_ext: 初期化済みのセンター効果の拡大ボーナス配列。

    :return: センター効果の拡大ボーナス配列。
    :rtype: np.ndarray
    """

    match context.buff.music:
        case MusicType.CUTE if context.live_songtype == SongType.CUTE:
            pass

        case MusicType.COOL if context.live_songtype == SongType.COOL:
            pass

        case MusicType.PASSION if context.live_songtype == SongType.PASSION:
            pass

        case _:
            LibsBackstageLogger.error("backstage.buff_dominant_duet: 楽曲要件を満たしていない。")
            return bonus_array_ext

    return breakdown2buffparts(context, bonus_array_ext)


appeal_funcname = {
    "全アピール値": buffpart_all,
    "ボーカルアピール値": buffpart_vocal,
    "ダンスアピール値": buffpart_dance,
    "ビジュアルアピール値": buffpart_visual,
    "ライフ": buffpart_life,
    "特技発動確率": buffpart_probability,
}
# アピール値（ボーカル、ダンス、ビジュアル、ライフ、特技発動確率）のみ。

buff_funcname = {
    # buff_cindarella_bless
    "シンデレラブレス": buff_cinderella_bless,
    # buff_resonance
    "レゾナンス・ボイス": buff_resonance,
    "レゾナンス・ステップ": buff_resonance,
    "レゾナンス・メイク": buff_resonance,
    # buff_dominant_duet
    "ドミナント・デュエット（ボイス＆ステップ）": buff_dominant_duet,
    "ドミナント・デュエット（ステップ＆メイク）": buff_dominant_duet,
    "ドミナント・デュエット（メイク＆ボイス）": buff_dominant_duet,
    # buff_duet
    "キュートデュエット（ボイス＆ステップ）": buff_duet,
    "クールデュエット（ボイス＆ステップ）": buff_duet,
    "パッションデュエット（ボイス＆ステップ）": buff_duet,
    "キュートデュエット（ステップ＆メイク）": buff_duet,
    "クールデュエット（ステップ＆メイク）": buff_duet,
    "パッションデュエット（ステップ＆メイク）": buff_duet,
    "キュートデュエット（メイク＆ボイス）": buff_duet,
    "クールデュエット（メイク＆ボイス）": buff_duet,
    "パッションデュエット（メイク＆ボイス）": buff_duet,
    # buff_cross
    "キュート・クロス・クール": buff_cross,
    "キュート・クロス・パッション": buff_cross,
    "クール・クロス・キュート": buff_cross,
    "クール・クロス・パッション": buff_cross,
    "パッション・クロス・キュート": buff_cross,
    "パッション・クロス・クール": buff_cross,
    # buff_single_appeal
    "キュートボイス": buff_single_appeal,
    "キュートステップ": buff_single_appeal,
    "キュートメイク": buff_single_appeal,
    "クールボイス": buff_single_appeal,
    "クールステップ": buff_single_appeal,
    "クールメイク": buff_single_appeal,
    "パッションボイス": buff_single_appeal,
    "パッションステップ": buff_single_appeal,
    "パッションメイク": buff_single_appeal,
    "シャイニーボイス": buff_single_appeal,
    "シャイニー・ステップ": buff_single_appeal,
    "トリコロール・ボイス": buff_single_appeal,
    "トリコロール・ステップ": buff_single_appeal,
    "トリコロール・メイク": buff_single_appeal,
    # buff_multi_appeal
    "キュートユニゾン": buff_multi_appeal,
    "クールユニゾン": buff_multi_appeal,
    "パッションユニゾン": buff_multi_appeal,
    "トリコロール・ユニゾン": buff_multi_appeal,
    "キュートブリリアンス": buff_multi_appeal,
    "クールブリリアンス": buff_multi_appeal,
    "パッションブリリアンス": buff_multi_appeal,
    "キュートプリンセス": buff_multi_appeal,
    "クールプリンセス": buff_multi_appeal,
    "パッションプリンセス": buff_multi_appeal,
    # buff_life
    "キュートエナジー": buff_life,
    "クールエナジー": buff_life,
    "パッションエナジー": buff_life,
    "キュートチアー": buff_life,
    "クールチアー": buff_life,
    "パッションチアー": buff_life,
    # buff_probability
    "キュートアビリティ": buff_probability,
    "クールアビリティ": buff_probability,
    "パッションアビリティ": buff_probability,
    "トリコロール・アビリティ": buff_probability,
}
# アピール値（ボーカル、ダンス、ビジュアル、ライフ、特技発動確率）に関わるセンター効果のみ。


class Calculator:
    """
    ゲスト、サポートメンバーを含むユニットのアピール値計算。
       - ボーカル・ダンス・ビジュアル・ライフ・特技発動率・特技継続期間

    :param Music music: デレステ譜面データ。
    """

    _idols: Idols = Idols()
    _episodes: Episodes = Episodes()
    _buffs: Buffs = Buffs()
    _skills: Skills = Skills()
    _potentials: Potentials = Potentials()

    def __init__(self, music: Music) -> None:

        self._music: Music = music

        LibsBackstageLogger.info(f"{self.__class__.__name__}.init: 初期化完了。")

    @property
    def isresonance(self) -> bool:
        """
        **True** の時、センター効果・レゾナンスが有効。**False** の時は、無効。
        """

        return self._resonance

    @property
    def unit(self) -> list:
        """
        ゲストを含むユニットメンバーのアピール値などのデータリスト。

        .. csv-table:: データリストの要素の型
            :header-rows: 1
            :stub-columns: 1

            "項目", "センター", "左隣り", "右隣り", "左端", "右端", "ゲスト"
            "0: エピソード名", "str", "str", "str", "str", "str", "str"
            "1: ボーカル", "int", "int", "int", "int", "int", "int"
            "2: ダンス", "int", "int", "int", "int", "int", "int"
            "3: ビジュアル", "int", "int", "int", "int", "int", "int"
            "4: ライフ", "int", "int", "int", "int", "int", "int"
            "5: 特技発動確率", "float", "float", "float", "float", "float", "float"
            "6: 特技継続期間", "float", "float", "float", "float", "float", "float"
        """

        return [
            [episode.episode for episode in self._unit_episodes if isinstance(episode, Episode)],
            np.ceil(self._unit[AppealIndices.VOCAL]).tolist(),
            np.ceil(self._unit[AppealIndices.DANCE]).tolist(),
            np.ceil(self._unit[AppealIndices.VISUAL]).tolist(),
            np.ceil(self._unit[AppealIndices.LIFE]).tolist(),
            self._unit[AppealIndices.PROBABILITY].tolist(),
            self._unit[AppealIndices.DURATION].tolist(),
        ]

    @property
    def supports(self) -> list:
        """
        サポートメンバーのアピール値のデータリスト。

        .. csv-table:: データリストの要素の型
            :header-rows: 1
            :stub-columns: 1

            "項目", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"
            "0: エピソード名", "str", "str", "str", "str", "str", "str", "str", "str", "str", "str"
            "1: ボーカル", "int", "int", "int", "int", "int", "int", "int", "int", "int", "int"
            "2: ダンス", "int", "int", "int", "int", "int", "int", "int", "int", "int", "int"
            "3: ビジュアル", "int", "int", "int", "int", "int", "int", "int", "int", "int", "int"
        """

        return [
            [episode.episode for episode in self._support_episodes if isinstance(episode, Episode)],
            np.ceil(self._support[AppealIndices.VOCAL]).tolist(),
            np.ceil(self._support[AppealIndices.DANCE]).tolist(),
            np.ceil(self._support[AppealIndices.VISUAL]).tolist(),
        ]

    def _log(self) -> None:
        """
        アピール値計算の結果をログに簡易出力する。
        """

        function_name = f"backstage.{self.__class__.__name__}._log: "

        LibsBackstageLogger.info(f"{function_name}メンバー {self.unit[0]}")
        LibsBackstageLogger.info(
            f"{function_name}アイドルタイプ {[self.__class__._episodes.get(episode).type.name for episode in self.unit[0]]}"
        )
        LibsBackstageLogger.info(
            f"{function_name}ドミナントアイドルタイプ {
                [self.__class__._episodes.get(episode).dominant.name for episode in self.unit[0]]
            }"
        )
        LibsBackstageLogger.info(
            f"{function_name}センター効果 {[self.__class__._episodes.get(episode).buff_class for episode in self.unit[0]]}"
        )
        LibsBackstageLogger.info(
            f"{function_name}特技 {[self.__class__._episodes.get(episode).skill_class for episode in self.unit[0]]}"
        )
        LibsBackstageLogger.info(f"{function_name}サポメン {self.supports[0]}")
        LibsBackstageLogger.info(
            f"{function_name}合計アピール {
                sum([sum(s) for s in self.unit[1:4]]) + sum([sum(s) for s in self.supports[1:4]])
            }"
        )
        LibsBackstageLogger.info(f"{function_name}ユニットアピール {sum([sum(s) for s in self.unit[1:4]])}")
        LibsBackstageLogger.info(f"{function_name}サポメンアピール {sum([sum(s) for s in self.supports[1:4]])}")
        # LibsBackstageLogger.info(f"{function_name}総ボーナス {self.unit}")  # センター効果（センター、ゲスト）？
        # LibsBackstageLogger.info(f"{function_name}タイプボーナス {self.unit}")  # 楽曲タイプ一致、ルーム効果？
        LibsBackstageLogger.info(f"{function_name}ボーカル {sum(self.unit[1]) + sum(self.supports[1])}")
        LibsBackstageLogger.info(f"{function_name}ダンス {sum(self.unit[2]) + sum(self.supports[2])}")
        LibsBackstageLogger.info(f"{function_name}ビジュアル {sum(self.unit[3]) + sum(self.supports[3])}")
        LibsBackstageLogger.info(f"{function_name}ライフ {sum(self.unit[4])}")

    def run(self, unit: Unit) -> None:
        """
        アピール値計算を実行する。

        :param Unit unit: ゲストを含むユニット。
        """

        # レゾナンスを適用するかどうかbool判定
        self._resonance: bool = False

        # ゲストを含むユニットメンバーのアピール値計算
        self._unit_episodes: list[Episode] = [
            self.__class__._episodes.get(episode) for episode in unit.positions.list() if isinstance(episode, str)
        ]

        unit_factors = [
            self._base(self._unit_episodes),  # 基礎値
            self._potential(self._unit_episodes),  # ポテンシャル補正
            self._musicbuff(self._unit_episodes),  # 楽曲タイプ一致効果
            self._roombuff(self._unit_episodes),  # ルーム効果
            self._centerbuff(self._unit_episodes),  # センター効果、およびゲストのセンター効果
            self._centerbuff(self._unit_episodes, 5) if len(self._unit_episodes) == 6 else np.zeros((6, 5)),
        ]

        self._unit = appeal_formula(unit_factors)

        # サポートメンバーの選出とアピール値計算
        self._support_episodes: list[Episode] = self._select_supports(unit)

        support_factors = [
            self._base(self._support_episodes),  # 基礎値
            self._potential(self._support_episodes),  # ポテンシャル補正
            self._musicbuff(self._support_episodes),  # 楽曲タイプ一致効果
        ]

        self._support = 0.5 * appeal_formula(support_factors)

        self._log()
        LibsBackstageLogger.info(f"{self.__class__.__name__}.run: アピール値計算完了。")

    def _select_supports(self, unit: Unit) -> list[Episode]:
        """
        サポートメンバーの選出を行う。

        ポテンシャル補正と楽曲タイプ一致効果を適用したアピール値（ボーカル・ダンス・ビジュアル）のトップ10をサポートメンバーとする。
        スターランク分の重複を許容し、ユニットメンバーとの重複分は差し引く。

        :param list[str] UnitEpisodes: ゲストを含むユニットメンバーのエピソード名リスト
        :return: サポートメンバーのエピソードリスト
        :rtype: list[Episode]
        """

        # 全エピソードのアピール値合計を計算し、リスト化。
        # まず、未所有（スターランク=0）を取り除く
        episode_all = sorted({episode for episode in self.__class__._episodes.gets() if episode.star_rank > 0})
        episode_all_factors = [
            self._base(episode_all),  # 基礎値
            self._potential(episode_all),  # ポテンシャル補正
            self._musicbuff(episode_all),  # 楽曲タイプ一致効果
        ]
        appeal_all = np.sum(
            np.ceil(0.5 * appeal_formula(episode_all_factors))[: AppealIndices.VISUAL + 1], axis=0
        ).tolist()

        # アピール値合計の高い順にエピソードをリスト化し、トップ10を選出。
        # スターランク分の重複を許容し、ユニットメンバーとの重複分は差し引く。
        appeal_episode_all = [(int(appeal), episode) for appeal, episode in zip(appeal_all, episode_all)]
        episode_support: list[Episode] = list()
        for appeal, episode in sorted(appeal_episode_all, reverse=True):
            for _ in range(episode.star_rank - 1 if episode in unit.positions.list() else episode.star_rank):
                episode_support.append(episode)
                if len(episode_support) == 10:
                    break
            else:
                continue
            break

        return episode_support

    def _base(self, episodes: list[Episode]) -> np.ndarray:
        """
        基礎値。

        ボーカル・ダンス・ビジュアル・ライフの値は、データベースから取り出した。
        特技発動率・特技継続期間は、データベースから取り出した値に特技レベル補正を適用した。

        :param list[Episode] episodes: エピソードリスト

        :return: 基礎値
        :rtype: np.ndarray
        """
        return np.array(
            [
                [episode.vocal for episode in episodes],
                [episode.dance for episode in episodes],
                [episode.visual for episode in episodes],
                [episode.life for episode in episodes],
                [
                    probability_value(self.__class__._skills.get(episode.skill).probability)
                    * (1.0 + (episode.skill_level - 1) / 18)
                    for episode in episodes
                ],
                [
                    duration_value(self.__class__._skills.get(episode.skill).duration)
                    * (1.0 + (episode.skill_level - 1) / 18)
                    for episode in episodes
                ],
            ]
        )

    def _potential(self, episodes: list[Episode]) -> np.ndarray:
        """
        ポテンシャル補正。

        ポテンシャル補正対象は、ボーカル・ダンス・ビジュアル・ライフ・特技発動率。
        特技継続期間は、非適用。

        :param list[Episode] episodes: エピソードリスト
        :return: ポテンシャル補正
        :rtype: np.ndarray
        """

        idols: list[Idol] = [
            self.__class__._idols.get(episode.ruby) for episode in episodes if isinstance(episode, Episode)
        ]

        return np.array(
            [
                [
                    self.__class__._potentials.value("ボーカル", episode.rare, idol.vocal)
                    for idol, episode in zip(idols, episodes)
                ],
                [
                    self.__class__._potentials.value("ダンス", episode.rare, idol.dance)
                    for idol, episode in zip(idols, episodes)
                ],
                [
                    self.__class__._potentials.value("ビジュアル", episode.rare, idol.visual)
                    for idol, episode in zip(idols, episodes)
                ],
                [
                    self.__class__._potentials.value("ライフ", episode.rare, idol.life)
                    for idol, episode in zip(idols, episodes)
                ],
                [
                    self.__class__._potentials.value("特技発動率", episode.rare, idol.skill)
                    for idol, episode in zip(idols, episodes)
                ],
                [0 for _ in episodes],
            ]
        )

    def _roombuff(self, episodes: list[Episode]) -> np.ndarray:
        """
        ルーム効果。

        ボーカル・ダンス・ビジュアルアピールにボーナスが加算される。
        キュート・クール・パッションのいづれかに必ず該当するので、一律に10%を付加する。

        :param list[Episode] episodes: エピソードリスト

        :return: ルーム効果
        :rtype: np.ndarray
        """

        return np.array(
            [
                [0.1 for _ in episodes],
                [0.1 for _ in episodes],
                [0.1 for _ in episodes],
                [0.0 for _ in episodes],
                [0.0 for _ in episodes],
                [0.0 for _ in episodes],
            ]
        )

    def _musicbuff(self, episodes: list[Episode]) -> np.ndarray:
        """
        楽曲タイプ一致効果。

        ボーカル・ダンス・ビジュアルアピールおよび特技発動確率にボーナスが加算される。
        楽曲タイプとアイドルタイプが一致する場合に、30%のボーナスが加算される。


        :param list[Episode] episodes: エピソードリスト

        :return: 楽曲タイプ一致効果
        :rtype: np.ndarray

        :todo: typematch() の実装中。
        """

        def basematch(type: SongType | IdolType, episodes: list[Episode]) -> np.ndarray:
            """
            楽曲タイプ一致効果のジェネリック（みたいな）関数。
            """

            return np.array(
                [
                    [0.3 if ismatch(type, episode.type) else 0 for episode in episodes],
                    [0.3 if ismatch(type, episode.type) else 0 for episode in episodes],
                    [0.3 if ismatch(type, episode.type) else 0 for episode in episodes],
                    [0.0 for _ in episodes],
                    [0.3 if ismatch(type, episode.type) else 0 for episode in episodes],
                    [0.0 for _ in episodes],
                ]
            )

        def typematch(buff: Buff, episodes: list[Episode]) -> np.ndarray:
            """
            センター効果パーツ適用効果のリストに、以下が含まれる場合：
              - ドミナント・デュエットのタイプ一致
              - シンデレラブレスで全員のセンター効果発動時、ドミナント・デュエットのタイプ一致
            楽曲タイプ一致効果有りのデータ配列を返す。それ以外は、要素がゼロのデータ配列。
            """

            lstype = self._music.song.type

            for part in buff.buffparts:
                match [buff.music, part.appeal]:
                    # センター効果パーツの適用効果のリストで検索

                    case [MusicType.COOL, AppealType.TYPEMATCH] if lstype == SongType.COOL:
                        # ドミナント・デュエットのタイプ一致

                        return basematch(part.member, episodes)

                    case AppealType.BLESS:
                        # ブレス
                        LibsBackstageLogger.error(
                            f"{self.__class__.__name__}._musicbuff(typematch): ちゃんと実装しろ！"
                        )
                        pass

            return np.zeros((len(AppealIndices), len(episodes)))

        lstype = self._music.song.type  # ライブの楽曲タイプ
        np3d = np.zeros((3, len(AppealIndices), len(episodes)))

        # 通常の楽曲タイプ一致
        np3d[0] = basematch(lstype, episodes)

        # ドミナント・デュエットのタイプ一致（センターあるいは、ブレスによる全員のセンター効果発動）
        buff = self.__class__._buffs.get(episodes[0].buff) if episodes else Buff()
        np3d[1] = typematch(buff, episodes)

        # ドミナント・デュエットのタイプ一致（ゲストあるいは、ブレスによる全員のセンター効果発動）
        if len(episodes) == 6:
            buff = self.__class__._buffs.get(episodes[5].buff)
            np3d[2] = typematch(buff, episodes)

        return np3d.max(axis=0)

    def _centerbuff(self, episodes: list[Episode], position: int = 0) -> np.ndarray:
        """
        センター効果（ボーカル・ダンス・ビジュアル・ライフ・特技発動率・特技継続期間）。

        :param list[Episode] episodes: エピソードリスト
        :param int position: センター効果を発動するメンバーの立ち位置。

        :return: センター効果データ配列。
        :rtype: np.ndarray
        """

        context = BuffContext(
            on_resonance=self._resonance,
            position=position,
            buff=self.__class__._buffs.get(episodes[position].buff),
            live_songtype=self._music.song.type,
            idoltypes_set={episode.type for episode in episodes},
            dominanttypes_set={episode.dominant for episode in episodes},
            skillclasses_set={episode.skill_class for episode in episodes},
            idoltypes_list=[episode.type for episode in episodes],
            dominanttypes_list=[episode.dominant for episode in episodes],
            episodes_list=episodes,
            buffs_list=[self.__class__._buffs.get(episode.buff) for episode in episodes],
        )

        if episodes[position].buff_class in buff_funcname:
            # アピール値の計算に必要、かつ実装済みのセンター効果
            result = buff_funcname[episodes[position].buff_class](context)
            self._resonance = context.on_resonance

        else:
            result = np.zeros((len(AppealIndices), len(episodes)))
            LibsBackstageLogger.error(
                f"{self.__class__.__name__}._centerbuff: {episodes[position].buff_class}は、未実装です。"
            )

        LibsBackstageLogger.debug(
            f"{self.__class__.__name__}._centerbuff: センター効果 - {','.join(str(result).splitlines())}"
        )
        return result


if __name__ == "__main__":
    print(__file__)
