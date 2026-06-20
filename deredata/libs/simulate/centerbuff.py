"""
センター効果ボーナスを計算する関数群のモジュール。
"""

import numpy as np
from typing import Any, Callable
from functools import wraps, partial
from dataclasses import dataclass, field
from functools import singledispatch

from deredata.libs.database.musics import SongType
from deredata.libs.database.enumerations import IdolType, DominantType, MusicType, UnitType
from deredata.libs.database.episodes import Episode
from deredata.libs.database.buffs import BuffPart, Buff, Buffs

from deredata.libs.simulate.enumerations import AppealIndices

from kivy.logger import Logger as LibsCenterbuffLogger

_buffs: Buffs = Buffs()


class CenterbuffError(Exception):
    """centerbuffモジュールのエラーハンドラ。"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsCenterbuffLogger.error(f"CenterbuffError: {args}")


@dataclass
class BuffPartContext:
    """
    センター効果パーツのコンテキストのデータクラス。

    アピールのボーナス配列を取得する際、必要となるセンター効果パーツに関わる各種条件を格納する。

    :param bool dominant: センター効果「ドミナント・デュエット」のセンター効果パーツかどうか。
    :param Episode episode: センター効果ボーナスを受け取るエピソード。
    :param BuffPart buffpart: センター効果パーツ。
    :param SongType song_type: ライブの楽曲タイプ。
    """

    buff_dominant_duet: bool = False
    episode: Episode = Episode()
    buffpart: BuffPart = BuffPart()
    song_type: SongType = SongType.ALL


@dataclass
class BuffContext:
    """
    センター効果のコンテキストのデータクラス。

    アピールのボーナス配列を取得する際、必要となるセンター効果に関わる各種条件を格納する。

    :param bool on_resonance: レゾナンス（全ての特技効果が重複時に加算）
    :param Episode episode: センター効果ボーナスを受け取るエピソード。
    :param Buff buff: センター効果
    :param SongType songtype: ライブの楽曲のタイプ
    :param list[IdolType] idol_types: ゲストを含むユニットメンバーのアイドルタイプリスト
    :param list[Episode] episodes: ゲストを含むユニットメンバーのエピソードリスト
    """

    on_resonance: bool = False
    episode: Episode = Episode()
    buff: Buff = Buff()
    song_type: SongType = SongType.ALL
    idol_types: list[IdolType] = field(default_factory=list)
    episodes: list[Episode] = field(default_factory=list)


@singledispatch
def idoltypematch(type: Any, idoltype: IdolType) -> bool:
    """
    タイプとアイドルタイプの一致を判定する。

    引数 *type* と 引数 *idoltype* のタイプが一致する場合に、``True`` を返す。
    それ以外は、 ``False`` を返す。

    :param Any type: アイドルタイプ（*IdolType*）／ドミナントアイドルタイプ（*DominantType*）。
    :param IdolType idoltype: アイドルタイプ。

    :return: タイプが一致する時は **True** 、一致しない時は **False** を返す。
    :rtype: bool
    """

    LibsCenterbuffLogger.error(f"centerbuff.idoltypematch: {type}が、不正です。")
    return False


@idoltypematch.register(IdolType)
def _(type: IdolType, idoltype: IdolType) -> bool:

    match [type, idoltype]:
        case [IdolType(itype), IdolType(stype)]:
            return True if itype.name == stype.name else False

        case _:
            LibsCenterbuffLogger.error(f"centerbuff.idoltypematch: {type},{idoltype} が、不正です。")
            return False


@idoltypematch.register(DominantType)
def _(type: DominantType, idoltype: IdolType) -> bool:
    match [type, idoltype]:
        case [DominantType(dtype), IdolType(stype)]:
            return True if dtype.name == stype.name else False

        case _:
            LibsCenterbuffLogger.error(f"centerbuff.songtypematch: {type},{idoltype} が、不正です。")
            return False


def buffpartwrap(func: Callable) -> Callable:
    """
    センター効果パーツのボーナス配列を返すラッパー関数。

    :ボーナス配列:
        要素がボーナスのNUMPY配列（軸0: アピールタイプ）。
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
        LibsCenterbuffLogger.debug(f"centerbuff.buffpartwrap: センター効果パーツ・{context.buffpart.name}を処理。")

        appealidices: list[AppealIndices] = partial(func, context)()

        # 後処理
        bonus: float = context.buffpart.value
        matchtype: IdolType = context.buffpart.member

        bonus_array: np.ndarray = np.zeros((len(AppealIndices),))
        for id in appealidices:
            if not context.buff_dominant_duet:
                bonus_array[id] = bonus if idoltypematch(context.episode.type, matchtype) else 0.0
            else:
                # ドミナントアイドルタイプリストが空リストではないので、センター効果「ドミナント・デュエット」と判定。
                bonus_array[id] = np.maximum(
                    bonus if idoltypematch(context.episode.type, matchtype) else 0.0,
                    bonus if idoltypematch(context.episode.dominant, matchtype) else 0.0,
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

        case MusicType.ALL if context.song_type == SongType.ALL:
            pass

        case MusicType.CUTE if context.song_type == SongType.CUTE:
            pass

        case MusicType.COOL if context.song_type == SongType.COOL:
            pass

        case MusicType.PASSION if context.song_type == SongType.PASSION:
            pass

        case _:
            LibsCenterbuffLogger.error(
                f"centerbuff.buffpart_all: この楽曲では、{context.buffpart.name} を適用できない。"
            )
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

    LibsCenterbuffLogger.error("centerbuff.buffpart_dance: センター効果・ワールドレベルのヘレン対応は、実装中です。")
    LibsCenterbuffLogger.error(
        "centerbuff.buffpart_dance: センター効果・ワールドレベルのフェイスオープン対応は、未実装です。"
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
            if buffpart.appeal in bonus_funcname:
                contexts.append(
                    BuffPartContext(
                        buff_dominant_duet=True,
                        episode=buffcontext.episode,
                        buffpart=buffpart,
                        song_type=buffcontext.song_type,
                    )
                )
    else:
        for buffpart in list(buffcontext.buff.buffparts):
            if buffpart.appeal in bonus_funcname:
                contexts.append(
                    BuffPartContext(
                        episode=buffcontext.episode,
                        buffpart=buffpart,
                        song_type=buffcontext.song_type,
                    )
                )

    for i, context in enumerate(contexts):
        if context.buffpart.appeal in bonus_funcname:
            bonus_array_ext[i] = bonus_funcname[context.buffpart.appeal](context)
        else:
            LibsCenterbuffLogger.error(f"centerbuff.breakdown2buffparts: {context.buffpart.appeal}は、未実装です。")

    return bonus_array_ext


def buffwrap(func: Callable) -> Callable:
    """
    センター効果のボーナス配列を返すラッパー関数。

    :ボーナス配列: 要素がボーナスのNUMPY配列（軸0: アピールタイプ）。
    :拡大ボーナス配列: 要素がボーナスのNUMPY配列（軸0: センター効果パーツ, 軸1: アピールタイプ）。
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
        LibsCenterbuffLogger.debug(f"centerbuff.buffwrap: センター効果・{context.buff.buff}を処理。")
        bonus_array_ext = np.zeros((len(context.buff.buffparts), len(AppealIndices)))

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

    # 要素がボーナスの変形ボーナス配列（軸0: メンバーのセンター効果, 軸1: アピールタイプ）。
    temp = np.zeros((len(context.episodes), len(AppealIndices)))

    for member, episode in enumerate(context.episodes):
        if episode.buff_class != "シンデレラブレス":
            LibsCenterbuffLogger.debug(f"centerbuff.buff_cinderella_bless: メンバー {member}")

            if episode.buff_class in centerbuff_funcname:
                # アピール値の計算に必要、かつ実装済みのセンター効果

                temp[member] = centerbuff_funcname[episode.buff_class](
                    BuffContext(
                        on_resonance=context.on_resonance,
                        episode=context.episode,
                        buff=_buffs.get(context.episodes[member].buff),
                        song_type=context.song_type,
                        idol_types=context.idol_types,
                        episodes=context.episodes,
                    )
                )

            else:
                LibsCenterbuffLogger.error(f"centerbuff.buff_cinderella_bless: {episode.buff_class}は、未実装です。")
                temp[member] = np.zeros((len(AppealIndices),))

    bonus_array_ext[0] = temp.max(axis=0)

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

    idol_typeset: set = set(context.idol_types)

    match context.buff.formation:
        case UnitType.NA:
            # キュートブリリアンス、クールブリリアンス、パッションブリリアンス。
            # キュート・ユニゾン、クール・ユニゾン、パッション・ユニゾン。
            pass

        case UnitType.ONLY_CUTE if idol_typeset == {IdolType.CUTE}:
            # キュートプリンセス（キュートアイドルのみ編成時）
            pass

        case UnitType.ONLY_COOL if idol_typeset == {IdolType.COOL}:
            # クールプリンセス（クールアイドルのみ編成時）
            pass

        case UnitType.ONLY_PASSION if idol_typeset == {IdolType.PASSION}:
            # パッションプリンセス（パッションアイドルのみ編成時）
            pass

        case UnitType.ALL if idol_typeset == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・ユニゾン（3タイプ全てのアイドル編成時）
            pass

        case _:
            LibsCenterbuffLogger.error("centerbuff.buff_multi_appeal: 編成要件を満たしていない。")
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

    idol_typeset: set = set(context.idol_types)

    match context.buff.formation:
        case UnitType.NA:
            # キュートボイス、キュートステップ、キュートメイク
            # クールボイス、クールステップ、クールメイク
            # パッションボイス、パッションステップ、パッションメイク
            # シャイニーボイス、シャイニー・ステップ

            pass

        case UnitType.ALL if idol_typeset == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・ボイス、トリコロール・ステップ、トリコロール・メイク（3タイプ全てのアイドル編成時）

            pass

        case _:
            LibsCenterbuffLogger.error("centerbuff.buff_single_appeal: 編成要件を満たしていない。")
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

    idol_typeset: set = set(context.idol_types)
    match context.buff.formation:
        case UnitType.NA:
            # キュートエナジー、クールエナジー、パッションエナジー

            pass

        case UnitType.ONLY_CUTE if idol_typeset == {IdolType.CUTE}:
            # キュートチアー（キュートアイドルのみ編成時）

            pass

        case UnitType.ONLY_COOL if idol_typeset == {IdolType.COOL}:
            # クールチアー（クールアイドルのみ編成時）

            pass
        case UnitType.ONLY_PASSION if idol_typeset == {IdolType.PASSION}:
            # パッションチアー（パッションアイドルのみ編成時）

            pass

        case _:
            LibsCenterbuffLogger.error("centerbuff.buff_life: 編成要件を満たしていない。")
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

    idol_typeset: set = set(context.idol_types)

    match context.buff.formation:
        case UnitType.NA:
            # キュートアビリティ、クールアビリティ、パッションアビリティ

            pass

        case UnitType.ALL if idol_typeset == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・アビリティ（3タイプ全てのアイドル編成時）

            pass

        case _:
            LibsCenterbuffLogger.error("centerbuff.buff_probability: 編成要件を満たしていない。")
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

    if len({episode.skill_class for episode in context.episodes}) >= 5:  # 5種類の特技編成時
        context.on_resonance = True  # 全ての特技効果が重複時に加算

    else:
        LibsCenterbuffLogger.error("centerbuff.buff_resonance: 特技が5種類未満のため、レゾナンスは無効。")
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

    idol_typeset: set = set(context.idol_types)
    match context.buff.formation:
        case UnitType.CUTE_AND_COOL | UnitType.COOL_AND_CUTE if idol_typeset >= {
            IdolType.CUTE,
            IdolType.COOL,
        }:
            pass

        case UnitType.COOL_AND_PASSION | UnitType.PASSION_AND_COOL if idol_typeset >= {
            IdolType.COOL,
            IdolType.PASSION,
        }:
            pass

        case UnitType.PASSION_AND_CUTE | UnitType.CUTE_AND_PASSION if idol_typeset >= {
            IdolType.PASSION,
            IdolType.CUTE,
        }:
            pass

        case _:
            LibsCenterbuffLogger.error("centerbuff.buff_cross: 編成要件を満たしていない。")
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

    idol_typeset: set = set(context.idol_types)
    match [context.buff.formation, context.buff.music]:
        case [UnitType.ONLY_CUTE, SongType.CUTE] if (
            idol_typeset == {IdolType.CUTE} and context.song_type == SongType.CUTE
        ):
            pass

        case [UnitType.ONLY_COOL, SongType.COOL] if (
            idol_typeset == {IdolType.COOL} and context.song_type == SongType.COOL
        ):
            pass

        case [UnitType.ONLY_PASSION, SongType.PASSION] if (
            idol_typeset == {IdolType.PASSION} and context.song_type == SongType.PASSION
        ):
            pass

        case _:
            LibsCenterbuffLogger.error("centerbuff.buff_duet: 編成要件もしくは楽曲要件を満たしていない。")
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
        case MusicType.CUTE if context.song_type == SongType.CUTE:
            pass

        case MusicType.COOL if context.song_type == SongType.COOL:
            pass

        case MusicType.PASSION if context.song_type == SongType.PASSION:
            pass

        case _:
            LibsCenterbuffLogger.error("centerbuff.buff_dominant_duet: 楽曲要件を満たしていない。")
            return bonus_array_ext

    return breakdown2buffparts(context, bonus_array_ext)


bonus_funcname: dict[str, Callable] = {
    "全アピール値": buffpart_all,
    "ボーカルアピール値": buffpart_vocal,
    "ダンスアピール値": buffpart_dance,
    "ビジュアルアピール値": buffpart_visual,
    "ライフ": buffpart_life,
    "特技発動確率": buffpart_probability,
}
# アピール（ボーカル、ダンス、ビジュアル、ライフ、特技発動確率）のボーナスのみ。

centerbuff_funcname: dict[str, Callable] = {
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
# アピール（ボーカル、ダンス、ビジュアル、ライフ、特技発動確率）のボーナスに関わるセンター効果のみ。


def bonus(
    episode: Episode,
    buff: Buff,
    episodes: list[Episode],
    song_type: SongType,
) -> tuple[np.ndarray, bool]:
    """
    センター効果ボーナス。

    :param Episode episode: センター効果ボーナスを受け取るエピソード。
    :param Buff buff: センター効果。
    :param list[Episode] episodes: ゲストを含むユニットメンバーのエピソードリスト。
    :param SongType songtype: ライブ楽曲の楽曲タイプ。

    :return: センター効果ボーナス、 レゾナンスが有効かどうか。
    :rtype: tuple[np.ndarray, bool]
    """

    if buff.buff in centerbuff_funcname:
        context = BuffContext(
            on_resonance=False,
            episode=episode,
            buff=buff,
            song_type=song_type,
            idol_types=[episode.type for episode in episodes],
            episodes=episodes,
        )

        result = centerbuff_funcname[buff.buff](context)
        return result, context.on_resonance

    LibsCenterbuffLogger.error(f"centerbuff.bonus: {buff.buff}は、未実装です。")
    return np.zeros((len(AppealIndices),)), False


if __name__ == "__main__":
    print(__file__)
