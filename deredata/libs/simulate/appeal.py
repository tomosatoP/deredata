"""
デレステの ``アピール値計算`` を扱うモジュール。

ライブのスコア計算前に、アピール値（ボーカル・ダンス・ビジュアル・ライフ・特技発動率・継続期間）を確定する。
まずは、通常のゲストメンバー有りの ``WIDEライブ`` のみ対応する。
``GrandLive`` や ``LiveCarnival（Booth効果）`` にも対応したい。

    .. csv-table:: 通常ライブとLiveCarnivalのライブの比較
      :header-rows: 1

      "項目", "通常ライブ", "LiveCarnival"
      "サポートメンバー", "有り", "無し"
      "ゲスト", "有り", "無し"
      "ゲストサポート", "無し", "センター以外に1名配置可能。ライブ全体で3名まで配置可能"
      "マイスタイル", "？", "ユニットに1名配置可能"

    .. csv-table:: LiveCarnivalのBooth効果
      :header-rows: 1

      "BOOTH効果", "説明"
      "キュート／クール／パッション", "対象タイプ楽曲のみ選択可能、対象タイプアイドルのアピール値アップ。"
      "全てのアイドル", "全アイドルのアピール値がアップ。"
      "ボーカル／ダンス／ビジュアル", "対象アピール値がアップ。"
      "ボーカルのみ／ダンスのみ／ビジュアルのみ", "対象アピール値がアップ、それ以外はゼロ。"
      "ユニットのライフ", "ユニットのライフに応じてアピール値がアップ。"
      "アイドルのスターランク", "アイドルのスターランクに応じてアピール値がアップ。"
      "プロデュースpt", "アイドルの開放されているプロデュースptに応じてアピール値がアップ。"
      "イベント指定アイドル", "イベント指定アイドルのアピール値アップ。"
      "選曲指定", "アピール値アップ。"
      "特技指定", "対象の特技を持つアイドルのみアピール値アップ。"

:入力:
    | ユニットメンバーのエピソード名リスト
    | ゲストメンバーのエピソード名
    | デレステ譜面データのファイル名

:出力:
    | レゾナンスの適否
    | ゲストを含むユニットメンバーのエピソード名リスト
    | ゲストを含むユニットメンバーのアピール値（ボーカル・ダンス・ビジュアル）
    | ゲストを含むユニットメンバーのライフ
    | ユニットメンバーの特技発動確率
    | ユニットメンバーの特技継続期間
    | サポートメンバーのエピソード名リスト
    | サポートメンバーのアピール値（ボーカル・ダンス・ビジュアル）

"""

import numpy as np
from enum import IntEnum
from typing import Any, Callable
from functools import singledispatch
from dataclasses import dataclass, field
from functools import wraps, partial

from deredata.libs.database.musics import SongType, Music
from deredata.libs.database.enums import IdolType, DominantType, MusicType, UnitType
from deredata.libs.database.idols import Idol, Idols
from deredata.libs.database.episodes import Episode, Episodes
from deredata.libs.database.units import Unit
from deredata.libs.database.buffs import BuffPart, Buff, Buffs, AppealType
from deredata.libs.database.skills import Skills, duration_value, probability_value
from deredata.libs.database.potentials import Potentials

from kivy.logger import Logger as LibsAppealLogger


class AppealError(Exception):
    """appealsモジュールのエラーハンドラ。"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsAppealLogger.error(f"AppealError: {args}")


class AppealRow(IntEnum):
    """
    アピール値データ（エピソード名を除く）順序の列挙クラス。

    :VOCAL: 0: ボーカル
    :DANCE: 1: ダンス
    :VISUAL: 2: ビジュアル
    :LIFE: 3: ライフ
    :PROBABILITY: 4: 特技発動率
    :DURATION: 5: 特技継続期間
    """

    VOCAL = 0  # ボーカル
    DANCE = 1  # ダンス
    VISUAL = 2  # ビジュアル
    LIFE = 3  # ライフ
    PROBABILITY = 4  # 特技発動率
    DURATION = 5  # 特技継続期間


@dataclass
class BoothEffect:
    """
    BOOTH効果のデータクラス（まだ中身無し）。
    """

    pass


@dataclass
class BuffPartContext:
    """
    センター効果パーツによるアピール値計算のコンテキストのデータクラス。

    :対象のアピール系統: ボーカル、ダンス、ビジュアル、ライフ、特技発動確率、特技継続期間

    :param BuffPart buffpart: センター効果パーツ。
    :param SongType livesong_type: ライブの楽曲タイプ。
    :param list[IdolType]|list[DominantType] idol_typelist:
      ユニットのアイドルタイプもしくはドミナントアイドルタイプのリスト。
    """

    buffpart: BuffPart = BuffPart()
    livesong_type: SongType = SongType.ALL
    idol_typelist: list[IdolType] | list[DominantType] = field(default_factory=list)


@dataclass
class BuffContext:
    """
    センター効果によるアピール値計算のコンテキストのデータクラス。

    :param bool on_resonance: レゾナンス（全ての特技効果が重複時に加算）
    :param int position: 立ち位置（センター、左隣、右隣、左端、右端、ゲスト）
    :param Buff buff: センター効果
    :param SongType livesong_type: ライブの楽曲のタイプ
    :param set[IdolType] idol_typeset: ゲストを含むユニットメンバーのアイドルタイプ集合
    :param set[DominantType] dominant_typeset: ゲストを含むユニットメンバーのドミナントアイドルタイプ集合
    :param set[str] skill_classset: ゲストを含むユニットメンバーの特技集合
    :param list[IdolType] idol_typelist: ゲストを含むユニットメンバーのアイドルタイプリスト
    :param list[DominantType] dominant_typelist: ゲストを含むユニットメンバーのドミナントアイドルタイプリスト
    :param list[Episode] episode_list: ゲストを含むユニットメンバーのエピソードリスト
    :param list[Buff] buff_list: ゲストを含むユニットメンバーのセンター効果リスト
    """

    on_resonance: bool = False
    position: int = 0
    buff: Buff = Buff()
    livesong_type: SongType = SongType.ALL
    idol_typeset: set[IdolType] = field(default_factory=set)
    dominant_typeset: set[DominantType] = field(default_factory=set)
    skill_classset: set[str] = field(default_factory=set)
    idol_typelist: list[IdolType] = field(default_factory=list)
    dominant_typelist: list[DominantType] = field(default_factory=list)
    episode_list: list[Episode] = field(default_factory=list)
    buff_list: list[Buff] = field(default_factory=list)


def appeal_formula(factors: list[np.ndarray]) -> np.ndarray:
    """
    アピール値の計算式。


    :アピール値:
      ボーカル・ダンス・ビジュアル、小数点以下切り上げ

      ゲストを含むユニットメンバーの場合:

        :math:`(基礎値+ポテンシャル補正)\\times(1.0+楽曲タイプ一致効果+ルーム効果+センター効果+ゲストのセンター効果)`

      サポートメンバーの場合:

        :math:`(基礎値+ポテンシャル補正)\\times(1.0+楽曲タイプ一致効果)\\times0.5`

    :ライフ:
      小数点以下切り上げ

      :math:`(基礎値+ポテンシャル補正)\\times(1.0+センター効果+ゲストのセンター効果)`

    :特技発動率:

      :math:`(基礎値\\times(1.0+\\dfrac{特技LV-1}{18})+ポテンシャル補正)\\times(1.0+楽曲タイプ一致効果+センター効果+ゲストのセンター効果)`

    :効果時間:

      :math:`基礎値\\times(1.0+\\dfrac{特技LV-1}{18})`

    :param list[np.ndarray] factors: 計算に用いる項目リスト。

    :return: 計算結果。
    :rtype: np.ndarray
    """

    return (factors[0] + factors[1]) * (1.0 + sum(factors[2:]))


@singledispatch
def ismatch(type: Any, member: IdolType | DominantType) -> bool:
    """
    タイプの一致を判定する。

    *type* 引数と *member* 引数のタイプが一致する場合に、``True`` を返す。
    それ以外は、 ``False`` を返す。

    :param SongType | IdolType type: 適用楽曲タイプ／適用アイドルタイプ。
    :param IdolType | DominantType member: 適用メンバーのアイドルタイプ／ドミナントアイドルタイプ。

    :return: タイプが一致する時は **True** 、一致しない時は **False** を返す。
    :rtype: bool
    """

    LibsAppealLogger.error("ismatch")
    return False


@ismatch.register(SongType)
def _(type: SongType, member: IdolType | DominantType) -> bool:
    """
    タイプ一致（SongType）。

    :param SongType type: 適用楽曲タイプ。
    :param IdolType | DominantType member: 適用メンバーのアイドルタイプ／ドミナントアイドルタイプ。

    :return: タイプが一致する時は **True** 、一致しない時は **False** を返す。
    :rtype: bool
    """

    match [type, member]:
        case [SongType.ALL, x]:  # noqa: F841
            return True

        case [SongType(stype), IdolType(idol)]:
            return True if stype.name == idol.name else False

        case [SongType(stype), DominantType(dominant)]:
            return True if stype.name == dominant.name else False

        case _:
            LibsAppealLogger.error("function ismatch: 一致しませんでした。")
            return False


@ismatch.register(IdolType)
def _(type: IdolType, member: IdolType | DominantType) -> bool:
    """
    タイプ一致（IdolType）。

    :param IdolType type: 適用アイドルタイプ。
    :param IdolType | DominantType member: 適用メンバーのアイドルタイプ／ドミナントアイドルタイプ。

    :return: タイプが一致する時は **True** 、一致しない時は **False** を返す。
    :rtype: bool
    """

    match [type, member]:
        case [IdolType.UNIT, x]:  # noqa: F841
            return True

        case [IdolType(itype), IdolType(idol)]:
            return True if itype == idol else False

        case [IdolType(itype), DominantType(dominant)]:
            return True if itype.name == dominant.name else False

        case _:
            LibsAppealLogger.error("function ismatch: 一致しませんでした。")
            return False


# 絶対値で比較して大きい方を返すnumpy.ufunc定義
abs_max = np.frompyfunc(lambda x, y: x if abs(x) >= abs(y) else y, 2, 1)


def buffpartwrap(func: Callable) -> Callable:
    """
    センター効果パーツのアピールデータ配列を返すラッパー関数。

    :前処理: アピールデータ配列を初期化する。
    :後処理: 無し。

    :param Callable func:
      アピール値の関数。
        :param BuffPartContext context: コンテキスト。
        :param np.ndarray datas: 初期化済みのアピールデータ配列。
        :return: アピールデータ配列。
        :rtype: np.ndarray

    :return: ラッパー関数
    :rtype: Callable
    """

    @wraps(func)
    def wrapper(context: BuffPartContext) -> np.ndarray:

        LibsAppealLogger.debug(f"センター効果パーツ・{context.buffpart.name}を処理。")

        appeal_data = np.zeros((len(AppealRow), len(context.idol_typelist)))

        return partial(func, context, appeal_data)()

    return wrapper


@buffpartwrap
def buffpart_all(context: BuffPartContext, data: np.ndarray) -> np.ndarray:
    """
    全アピール（ボーカル、ダンス、ビジュアル）値。

    :param BuffPartContext context: コンテキスト。
    :param np.ndarray data: 初期化済みのアピールデータ配列。

    :return: アピールデータ配列。
    :rtype: np.ndarray
    """

    value: float = context.buffpart.value
    member: IdolType = context.buffpart.member
    types: list[IdolType] | list[DominantType] = context.idol_typelist

    def value_by_membermatch() -> None:
        for row in [AppealRow.VOCAL, AppealRow.DANCE, AppealRow.VISUAL]:
            data[row] = np.array([value if ismatch(member, type) else 0.0 for type in types])

    match context.buffpart.music:
        # 適用楽曲

        case MusicType.NA:
            value_by_membermatch()

        case MusicType.ALL if context.livesong_type == SongType.ALL:
            value_by_membermatch()

        case MusicType.CUTE if context.livesong_type == SongType.CUTE:
            value_by_membermatch()

        case MusicType.COOL if context.livesong_type == SongType.COOL:
            value_by_membermatch()

        case MusicType.PASSION if context.livesong_type == SongType.PASSION:
            value_by_membermatch()

    return data


@buffpartwrap
def buffpart_vocal(context: BuffPartContext, data: np.ndarray) -> np.ndarray:
    """
    ボーカルアピール値。

    :param BuffPartContext context: コンテキスト。
    :param np.ndarray data: 初期化済みのアピールデータ配列。

    :return: アピールデータ配列。
    :rtype: np.ndarray
    """

    value: float = context.buffpart.value
    member: IdolType = context.buffpart.member
    types: list[IdolType] | list[DominantType] = context.idol_typelist

    data[AppealRow.VOCAL] = np.array([value if ismatch(member, type) else 0.0 for type in types])

    return data


@buffpartwrap
def buffpart_dance(context: BuffPartContext, data: np.ndarray) -> np.ndarray:
    """
    ダンスアピール値。

    :param BuffPartContext context: コンテキスト。
    :param np.ndarray data: 初期化済みのアピールデータ配列。

    :return: アピールデータ配列。
    :rtype: np.ndarray

    :todo: ワールドオープン（ヘレン）
    """

    value: float = context.buffpart.value
    member: IdolType = context.buffpart.member
    types: list[IdolType] | list[DominantType] = context.idol_typelist

    data[AppealRow.DANCE] = np.array([value if ismatch(member, type) else 0.0 for type in types])

    return data


@buffpartwrap
def buffpart_visual(context: BuffPartContext, data: np.ndarray) -> np.ndarray:
    """
    ビジュアルアピール値。

    :param BuffPartContext context: コンテキスト。
    :param np.ndarray data: 初期化済みのアピールデータ配列。

    :return: アピールデータ配列。
    :rtype: np.ndarray
    """

    value: float = context.buffpart.value
    member: IdolType = context.buffpart.member
    types: list[IdolType] | list[DominantType] = context.idol_typelist

    data[AppealRow.VISUAL] = np.array([value if ismatch(member, type) else 0.0 for type in types])

    return data


@buffpartwrap
def buffpart_life(context: BuffPartContext, data: np.ndarray) -> np.ndarray:
    """
    ライフ値。

    :param BuffPartContext context: コンテキスト。
    :param np.ndarray data: 初期化済みのアピールデータ配列。

    :return: アピールデータ配列。
    :rtype: np.ndarray
    """

    value: float = context.buffpart.value
    member: IdolType = context.buffpart.member
    types: list[IdolType] | list[DominantType] = context.idol_typelist

    data[AppealRow.LIFE] = np.array([value if ismatch(member, type) else 0.0 for type in types])

    return data


@buffpartwrap
def buffpart_probability(context: BuffPartContext, data: np.ndarray) -> np.ndarray:
    """
    特技発動確率値。

    :param BuffPartContext context: コンテキスト。
    :param np.ndarray data: 初期化済みのアピールデータ配列。

    :return: アピールデータ配列。
    :rtype: np.ndarray
    """

    value: float = context.buffpart.value
    member: IdolType = context.buffpart.member
    types: list[IdolType] | list[DominantType] = context.idol_typelist

    data[AppealRow.PROBABILITY] = np.array([value if ismatch(member, type) else 0.0 for type in types])

    return data


def breakdown2buffparts(contexts: list[BuffPartContext], data: np.ndarray) -> np.ndarray:
    """
    センター効果をセンター効果パーツに展開して、センター効果データ配列を返す。

    :param list[BuffPartContext] contexts: センター効果パーツコンテキストのリスト。
    :param np.ndarray data: 初期化済みのセンター効果データ配列。

    :return: センター効果データ配列
    :rtype: np.ndarray
    """

    for i, context in enumerate(contexts):
        if context.buffpart.appeal in appeal_funcname:
            data[i] = appeal_funcname[context.buffpart.appeal](context)

    return data


def buffwrap(func: Callable) -> Callable:
    """
    センター効果のデータ配列を返すラッパー関数。

    :前処理: センター効果パーツ分のセンター効果データ配列を初期化する。
    :後処理: センター効果データ配列を最も効果の大きい要素にする。

    :param Callable func:
      センター効果の関数。
        :param BuffContext context: コンテキスト。
        :param np.ndarray datas: 初期化済みのセンター効果データ配列。
        :return: センター効果データ配列。
        :rtype: np.ndarray

    :return: ラッパー関数
    :rtype: Callable
    """

    @wraps(func)
    def wrapper(context: BuffContext) -> np.ndarray:

        LibsAppealLogger.debug(f"センター効果・{context.buff.buff}を処理。")

        buff_data = np.zeros((len(context.buff.buffparts), len(AppealRow), len(context.episode_list)))
        result = partial(func, context, buff_data)

        return abs_max.reduce(result()[:])

    return wrapper


@buffwrap
def buff_cinderella_bless(context: BuffContext, data: np.ndarray) -> np.ndarray:
    """
    シンデレラブレス系センター効果。

    :センター効果説明:
      ゲストを含むユニット編成アイドル全員のセンター効果を発揮し、最も高い効果を適用

    :param BuffContext context: センター効果コンテキスト。
    :param np.ndarray data: センター効果データ配列。

    :return: センター効果データ配列
    :rtype: np.ndarray
    """

    match context.position:
        # 立ち位置

        case 0 | 5:
            # センターもしくはゲストのセンター効果：シンデレラブレス。

            temp = np.zeros((len(context.episode_list), len(AppealRow), len(context.episode_list)))

            for member, episode in enumerate(context.episode_list):
                if member != context.position or episode.buff_class != "シンデレラブレス":
                    LibsAppealLogger.debug(f"シンデレラブレス[{context.position}]  {member}人目")

                    if episode.buff_class in buff_funcname:
                        # アピール値の計算に必要、かつ実装済みのセンター効果

                        temp[member] = buff_funcname[episode.buff_class](
                            BuffContext(
                                position=member,
                                buff=Calculator._buffs.get(context.episode_list[member].buff),
                                livesong_type=context.livesong_type,
                                idol_typeset=context.idol_typeset,
                                dominant_typeset=context.dominant_typeset,
                                skill_classset=context.skill_classset,
                                idol_typelist=context.idol_typelist,
                                dominant_typelist=context.dominant_typelist,
                                episode_list=context.episode_list,
                                buff_list=context.buff_list,
                            )
                        )

                    else:
                        LibsAppealLogger.debug(f"{episode.buff_class}は、未実装です。")
                        temp[member] = np.zeros((len(AppealRow), len(context.episode_list)))

            data[0] = temp.max(axis=0)

        case _:
            # 以外（効果がセンターもしくはゲストと重複するだけなので、何もしない）。
            LibsAppealLogger.debug("シンデレラブレス: センター、ゲスト以外")

    return data


@buffwrap
def buff_multi_appeal(context: BuffContext, data: np.ndarray) -> np.ndarray:
    """
    全アピール系センター効果。

      | キュートブリリアンス、クールブリリアンス、パッションブリリアンス。
      | キュートプリンセス、クールプリンセス、パッションプリンセス。
      | キュート・ユニゾン、クール・ユニゾン、パッション・ユニゾン。
      | トリコロール・ユニゾン。

    :センター効果説明:
      | __アイドルの全アピール値__%アップ
      | __アイドルの全アピール値__%アップ、__楽曲なら__%アップ
      | 3タイプ全てのアイドル編成時、全員の全アピール値__%アップ、全タイプ楽曲なら__%アップ

    :param BuffContext context: センター効果コンテキスト。
    :param np.ndarray data: センター効果データ配列。

    :return: センター効果データ配列
    :rtype: np.ndarray
    """

    match context.buff.formation:
        case UnitType.NA:
            # キュートブリリアンス、クールブリリアンス、パッションブリリアンス。
            # キュート・ユニゾン、クール・ユニゾン、パッション・ユニゾン。
            pass

        case UnitType.ONLY_CUTE if context.idol_typeset == {IdolType.CUTE}:
            # キュートプリンセス（キュートアイドルのみ編成時）
            pass

        case UnitType.ONLY_COOL if context.idol_typeset == {IdolType.COOL}:
            # クールプリンセス（クールアイドルのみ編成時）
            pass

        case UnitType.ONLY_PASSION if context.idol_typeset == {IdolType.PASSION}:
            # パッションプリンセス（パッションアイドルのみ編成時）
            pass

        case UnitType.ALL if context.idol_typeset == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・ユニゾン（3タイプ全てのアイドル編成時）
            pass

        case _:
            LibsAppealLogger.error("buff_multi_appeal: 対象外の編成")
            return data

    contexts: list[BuffPartContext] = list()
    for buffpart in list(context.buff.buffparts):
        if buffpart.appeal in appeal_funcname:
            contexts.append(BuffPartContext(buffpart, context.livesong_type, context.idol_typelist))

    return breakdown2buffparts(contexts, data)


@buffwrap
def buff_single_appeal(context: BuffContext, data: np.ndarray) -> np.ndarray:
    """
    ボイス、ダンス、ビジュアル系センター効果。

      | キュートボイス、キュートステップ、キュートメイク
      | クールボイス、クールステップ、クールメイク
      | パッションボイス、パッションステップ、パッションメイク
      | シャイニーボイス、シャイニー・ステップ
      | トリコロール・ボイス、トリコロール・ステップ、トリコロール・メイク

    :センター効果説明:
      | __アイドルの__アピール値__%アップ
      | 全員の__アピール値__%アップ
      | 3タイプ全てのアイドル編成時、全員の__アピール値__%アップ

    :param BuffContext context: センター効果コンテキスト。
    :param np.ndarray data: センター効果データ配列。

    :return: センター効果データ配列
    :rtype: np.ndarray
    """

    match context.buff.formation:
        case UnitType.NA:
            # キュートボイス、キュートステップ、キュートメイク
            # クールボイス、クールステップ、クールメイク
            # パッションボイス、パッションステップ、パッションメイク
            # シャイニーボイス、シャイニー・ステップ

            pass

        case UnitType.ALL if context.idol_typeset == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・ボイス、トリコロール・ステップ、トリコロール・メイク（3タイプ全てのアイドル編成時）

            pass

        case _:
            LibsAppealLogger.error("buff_single_appeal: 対象外の編成")
            return data

    contexts: list[BuffPartContext] = list()
    for buffpart in list(context.buff.buffparts):
        if buffpart.appeal in appeal_funcname:
            contexts.append(BuffPartContext(buffpart, context.livesong_type, context.idol_typelist))

    return breakdown2buffparts(contexts, data)


@buffwrap
def buff_life(context: BuffContext, data: np.ndarray) -> np.ndarray:
    """
    ライフ値系センター効果。

      | キュートエナジー、クールエナジー、パッションエナジー
      | キュートチアー、クールチアー、パッションチアー

    :センター効果説明:
      | __アイドルのライフ__%アップ
      | __アイドルのみ編成時、全員のライフ__%アップ

    :param BuffContext context: センター効果コンテキスト。
    :param np.ndarray data: センター効果データ配列。

    :return: センター効果データ配列
    :rtype: np.ndarray
    """

    match context.buff.formation:
        case UnitType.NA:
            # キュートエナジー、クールエナジー、パッションエナジー

            pass

        case UnitType.ONLY_CUTE if context.idol_typeset == {IdolType.CUTE}:
            # キュートチアー（キュートアイドルのみ編成時）

            pass

        case UnitType.ONLY_COOL if context.idol_typeset == {IdolType.COOL}:
            # クールチアー（クールアイドルのみ編成時）

            pass
        case UnitType.ONLY_PASSION if context.idol_typeset == {IdolType.PASSION}:
            # パッションチアー（パッションアイドルのみ編成時）

            pass

        case _:
            LibsAppealLogger.error("buff_life: 対象外の編成")
            return data

    contexts: list[BuffPartContext] = list()
    for buffpart in list(context.buff.buffparts):
        if buffpart.appeal in appeal_funcname:
            contexts.append(BuffPartContext(buffpart, context.livesong_type, context.idol_typelist))

    return breakdown2buffparts(contexts, data)


@buffwrap
def buff_probability(context: BuffContext, data: np.ndarray) -> np.ndarray:
    """
    特技発動確率系センター効果。

      | キュートアビリティ、クールアビリティ、パッションアビリティ
      | トリコロール・アビリティ

    :センター効果説明:
      | __アイドルの特技発動確率__%アップ
      | 3タイプ全てのアイドル編成時、全員の特技発動確率__%アップ

    :param BuffContext context: センター効果コンテキスト。
    :param np.ndarray data: センター効果データ配列。

    :return: センター効果データ配列
    :rtype: np.ndarray
    """

    match context.buff.formation:
        case UnitType.NA:
            # キュートアビリティ、クールアビリティ、パッションアビリティ

            pass

        case UnitType.ALL if context.idol_typeset == {IdolType.CUTE, IdolType.COOL, IdolType.PASSION}:
            # トリコロール・アビリティ（3タイプ全てのアイドル編成時）

            pass

        case _:
            LibsAppealLogger.error("buff_probability: 対象外の編成")
            return data

    contexts: list[BuffPartContext] = list()
    for buffpart in list(context.buff.buffparts):
        if buffpart.appeal in appeal_funcname:
            contexts.append(BuffPartContext(buffpart, context.livesong_type, context.idol_typelist))

    return breakdown2buffparts(contexts, data)


@buffwrap
def buff_resonance(context: BuffContext, data: np.ndarray) -> np.ndarray:
    """
    レゾナンス系センター効果。

      | レゾナンス・ボイス。
      | レゾナンス・ステップ。
      | レゾナンス・メイク。

    :センター効果説明:
      5種類の特技編成時、__以外のアピール値を100%ダウンし、全ての特技効果が重複時に加算

    :param BuffContext context: センター効果コンテキスト。
    :param np.ndarray data: センター効果データ配列。

    :return: センター効果データ配列
    :rtype: np.ndarray
    """

    if len(context.skill_classset) >= 5:
        # 5種類の特技編成時

        context.on_resonance = True
        # 全ての特技効果が重複時に加算

        contexts: list[BuffPartContext] = list()
        for buffpart in list(context.buff.buffparts):
            if buffpart.appeal in appeal_funcname:
                contexts.append(BuffPartContext(buffpart, context.livesong_type, context.idol_typelist))

        return breakdown2buffparts(contexts, data)

    LibsAppealLogger.error("buff_resonance: 対象外の編成")
    return data


@buffwrap
def buff_cross(context: BuffContext, data: np.ndarray) -> np.ndarray:
    """
    クロス系センター効果。

      | キュート・クロス・クール、キュート・クロス・パッション
      | クール・クロス・キュート、クール・クロス・パッション
      | パッション・クロス・キュート、パッション・クロス・クール

    :センター効果説明:
      | キュートとクールのアイドル編成時、全員の全アピール値__%アップ、獲得ファン数が__%アップ
      | キュートとパッションのアイドル編成時、全員の全アピール値__%アップ、獲得ファン数が__%アップ
      | クールとキュートのアイドル編成時、全員の全アピール値__%アップ、全員の特技発動率__%アップ
      | クールとパッションのアイドル編成時、全員の全アピール値__%アップ、全員の特技発動率__%アップ
      | パッションとキュートのアイドル編成時、全員の全アピール値__%アップ、全員のライフ__%アップ
      | パッションとクールのアイドル編成時、全員の全アピール値__%アップ、全員のライフ__%アップ

    :param BuffContext context: センター効果コンテキスト。
    :param np.ndarray data: センター効果データ配列。

    :return: センター効果データ配列
    :rtype: np.ndarray
    """

    match context.buff.formation:
        case UnitType.CUTE_AND_COOL | UnitType.COOL_AND_CUTE if context.idol_typeset >= {
            IdolType.CUTE,
            IdolType.COOL,
        }:
            pass

        case UnitType.COOL_AND_PASSION | UnitType.PASSION_AND_COOL if context.idol_typeset >= {
            IdolType.COOL,
            IdolType.PASSION,
        }:
            pass

        case UnitType.PASSION_AND_CUTE | UnitType.CUTE_AND_PASSION if context.idol_typeset >= {
            IdolType.PASSION,
            IdolType.CUTE,
        }:
            pass

        case _:
            LibsAppealLogger.error("buff_cross: 対象外の編成")
            return data

    contexts: list[BuffPartContext] = list()
    for buffpart in list(context.buff.buffparts):
        if buffpart.appeal in appeal_funcname:
            contexts.append(BuffPartContext(buffpart, context.livesong_type, context.idol_typelist))

    return breakdown2buffparts(contexts, data)


@buffwrap
def buff_duet(context: BuffContext, data: np.ndarray) -> np.ndarray:
    """
    デュエット系センター効果。

      | キュート・デュエット（ボイス＆ステップ）、クール・デュエット（ボイス＆ステップ）、\
          パッション・デュエット（ボイス＆ステップ）。
      | キュート・デュエット（ステップ＆メイク）、クール・デュエット（ステップ＆メイク）、\
          パッション・デュエット（ステップ＆メイク）。
      | キュート・デュエット（メイク＆ボイス）、クール・デュエット（メイク＆ボイス）、\
          パッション・デュエット（メイク＆ボイス）。

    :センター効果説明:
      | __アイドルのみ編成時、__楽曲で全員のダンス＆ビジュアルアピール値__%アップ
      | __アイドルのみ編成時、__楽曲で全員のビジュアル＆ボーカルアピール値__%アップ
      | __アイドルのみ編成時、__楽曲で全員のボーカル＆ダンスアピール値__%アップ

    :param BuffContext context: センター効果コンテキスト。
    :param np.ndarray data: センター効果データ配列。

    :return: センター効果データ配列
    :rtype: np.ndarray
    """

    match [context.buff.formation, context.buff.music]:
        case [UnitType.ONLY_CUTE, SongType.CUTE] if (
            context.idol_typeset == {IdolType.CUTE} and context.livesong_type == SongType.CUTE
        ):
            pass

        case [UnitType.ONLY_COOL, SongType.COOL] if (
            context.idol_typeset == {IdolType.COOL} and context.livesong_type == SongType.COOL
        ):
            pass

        case [UnitType.ONLY_PASSION, SongType.PASSION] if (
            context.idol_typeset == {IdolType.PASSION} and context.livesong_type == SongType.PASSION
        ):
            pass

        case _:
            LibsAppealLogger.error("buff_duet: 対象外の編成、楽曲")
            return data

    contexts: list[BuffPartContext] = list()
    for buffpart in list(context.buff.buffparts):
        if buffpart.appeal in appeal_funcname:
            contexts.append(BuffPartContext(buffpart, context.livesong_type, context.idol_typelist))

    return breakdown2buffparts(contexts, data)


@buffwrap
def buff_dominant_duet(context: BuffContext, data: np.ndarray) -> np.ndarray:
    """
    ドミナント・デュエット系センター効果。

      | ドミナント・デュエット（ボイス＆ステップ）。
      | ドミナント・デュエット（ステップ＆メイク）。
      | ドミナント・デュエット（メイク＆ボイス）。

    :センター効果説明:
      __楽曲で__アイドルにタイプボーナスが発生し__アピール値150%アップ、__アイドルの__アピール値160%アップ

    :param BuffContext context: センター効果コンテキスト。
    :param np.ndarray data: センター効果データ配列。

    :return: センター効果データ配列
    :rtype: np.ndarray
    """

    match context.buff.music:
        case MusicType.CUTE if context.livesong_type == SongType.CUTE:
            pass

        case MusicType.COOL if context.livesong_type == SongType.COOL:
            pass

        case MusicType.PASSION if context.livesong_type == SongType.PASSION:
            pass

        case _:
            LibsAppealLogger.error("buff_dominant_duet: 対象外の楽曲")
            return data

    for i, buffpart in enumerate(context.buff.buffparts):
        if buffpart.appeal in appeal_funcname:
            # アイドルタイプ
            idoldata = appeal_funcname[buffpart.appeal](
                BuffPartContext(buffpart, context.livesong_type, context.idol_typelist)
            )

            # ドミナントアイドルタイプ
            dominantdata = appeal_funcname[buffpart.appeal](
                BuffPartContext(buffpart, context.livesong_type, context.dominant_typelist)
            )

            data[i] = np.maximum(idoldata, dominantdata)
    return data


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
    "キュート・デュエット（ボイス＆ステップ）": buff_duet,
    "クール・デュエット（ボイス＆ステップ）": buff_duet,
    "パッション・デュエット（ボイス＆ステップ）": buff_duet,
    "キュート・デュエット（ステップ＆メイク）": buff_duet,
    "クール・デュエット（ステップ＆メイク）": buff_duet,
    "パッション・デュエット（ステップ＆メイク）": buff_duet,
    "キュート・デュエット（メイク＆ボイス）": buff_duet,
    "クール・デュエット（メイク＆ボイス）": buff_duet,
    "パッション・デュエット（メイク＆ボイス）": buff_duet,
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
    "キュート・ユニゾン": buff_multi_appeal,
    "クール・ユニゾン": buff_multi_appeal,
    "パッション・ユニゾン": buff_multi_appeal,
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
    ゲスト、サポートメンバーを含むアピール値計算。
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

        LibsAppealLogger.info(f"{self.__class__.__name__}.init: 初期化完了。")

    @classmethod
    def load(cls) -> None:
        """
        データベースを読み込む。

        | アイドル、エピソード、センター効果、特技、ポテンシャルのデータベースを読み込む。
        | :strong:`データベースに変更があれば、再実行する。`
        """

        cls._idols.load()
        cls._episodes.load()
        cls._buffs.load()
        cls._skills.load()
        cls._potentials.load()

        LibsAppealLogger.info(f"{cls.__name__}.load: データベース読み込み完了。")

    @property
    def isresonance(self) -> bool:
        """
        True の時、センター効果・レゾナンスが有効。False の時は、無効。
        """

        return self._resonance

    @property
    def unit(self) -> list:
        """
        ゲストを含むユニットメンバーのアピール値などのデータリスト。


        =========== ========== ============= ============== ========= ========== =====
        parameters  Center     Left neighbor Right neighbor Left edge Right edge Guest
        =========== ========== ============= ============== ========= ========== =====
        Episode     STR        STR           STR            STR       STR        STR
        Vocal       INT        INT           INT            INT       INT        INT
        Dance       INT        INT           INT            INT       INT        INT
        Visual      INT        INT           INT            INT       INT        INT
        Life        INT        INT           INT            INT       INT        INT
        Probability FLOAT      FLOAT         FLOAT          FLOAT     FLOAT      FLOAT
        Duration    FLOAT      FLOAT         FLOAT          FLOAT     FLOAT      FLOAT
        =========== ========== ============= ============== ========= ========== =====

        """

        return [
            [episode.episode for episode in self._unit_episodes if isinstance(episode, Episode)],
            np.ceil(self._unit[AppealRow.VOCAL]).tolist(),
            np.ceil(self._unit[AppealRow.DANCE]).tolist(),
            np.ceil(self._unit[AppealRow.VISUAL]).tolist(),
            np.ceil(self._unit[AppealRow.LIFE]).tolist(),
            self._unit[AppealRow.PROBABILITY].tolist(),
            self._unit[AppealRow.DURATION].tolist(),
        ]

    @property
    def supports(self) -> list:
        """
        サポートメンバーのアピール値のデータリスト。

        =========== ===========
        parameters  Support(10)
        =========== ===========
        Episode     STR
        Vocal       INT
        Dance       INT
        Visual      INT
        =========== ===========

        """

        return [
            [episode.episode for episode in self._support_episodes if isinstance(episode, Episode)],
            np.ceil(self._support[AppealRow.VOCAL]).tolist(),
            np.ceil(self._support[AppealRow.DANCE]).tolist(),
            np.ceil(self._support[AppealRow.VISUAL]).tolist(),
        ]

    def run(self, unit: Unit) -> None:
        """
        アピール値計算を実行する。

        :param list[str] UnitEpisodes: ゲストを含むユニットメンバーのエピソード名リスト。
        """

        # レゾナンスを適用するかどうかbool判定
        self._resonance: bool = False

        # ゲストを含むユニットメンバーのアピール値計算
        self._unit_episodes: list[Episode] = [
            Calculator._episodes.get(episode) for episode in unit.positions.list() if isinstance(episode, str)
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

        LibsAppealLogger.info(f"{self.__class__.__name__}.run: アピール値計算完了。")

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
        # まず未所有（スターランク=0）を取り除く
        episode_all = sorted({episode for episode in Calculator._episodes.gets() if episode.star_rank > 0})
        episode_all_factors = [
            self._base(episode_all),  # 基礎値
            self._potential(episode_all),  # ポテンシャル補正
            self._musicbuff(episode_all),  # 楽曲タイプ一致効果
        ]
        appeal_all = np.sum(np.ceil(0.5 * appeal_formula(episode_all_factors))[: AppealRow.VISUAL + 1], axis=0).tolist()

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
                    probability_value(Calculator._skills.get(episode.skill).probability)
                    * (1.0 + (episode.skill_level - 1) / 18)
                    for episode in episodes
                ],
                [
                    duration_value(Calculator._skills.get(episode.skill).duration)
                    * (1.0 + (episode.skill_level - 1) / 18)
                    for episode in episodes
                ],
            ]
        )

    def _potential(self, episodes: list[Episode]) -> np.ndarray:
        """
        ポテンシャル補正。

        ポテンシャル補正対象は、ボーカル・ダンス・ビジュアル・ライフ・特技発動率。
        特技継続期間は、補正無し。

        :param list[Episode] episodes: エピソードリスト
        :return: ポテンシャル補正
        :rtype: np.ndarray
        """

        idols: list[Idol] = [
            Calculator._idols.get(episode.ruby) for episode in episodes if isinstance(episode, Episode)
        ]

        return np.array(
            [
                [
                    Calculator._potentials.value("ボーカル", episode.rare, idol.vocal)
                    for idol, episode in zip(idols, episodes)
                ],
                [
                    Calculator._potentials.value("ダンス", episode.rare, idol.dance)
                    for idol, episode in zip(idols, episodes)
                ],
                [
                    Calculator._potentials.value("ビジュアル", episode.rare, idol.visual)
                    for idol, episode in zip(idols, episodes)
                ],
                [
                    Calculator._potentials.value("ライフ", episode.rare, idol.life)
                    for idol, episode in zip(idols, episodes)
                ],
                [
                    Calculator._potentials.value("特技発動率", episode.rare, idol.skill)
                    for idol, episode in zip(idols, episodes)
                ],
                [0 for _ in episodes],
            ]
        )

    def _roombuff(self, episodes: list[Episode]) -> np.ndarray:
        """
        ルーム効果。

        ルーム効果対象は、ボーカル・ダンス・ビジュアル。
        キュート・クール・パッションのいづれかに必ず該当するので、一律に10%を付加する。
        ライフ、特技発動率、特技継続期間は、対象外。

        :param list[Episode] episodes: エピソードリスト
        :return: ルーム効果
        :rtype: np.ndarray
        """

        return np.array(
            [[0.1 for _ in episodes] for _ in [AppealRow.VOCAL, AppealRow.DANCE, AppealRow.VISUAL]]
            + [[0.0 for _ in episodes] for _ in [AppealRow.LIFE, AppealRow.PROBABILITY, AppealRow.DURATION]]
        )

    def _musicbuff(self, episodes: list[Episode]) -> np.ndarray:
        """
        楽曲タイプ一致効果（ボーカル・ダンス・ビジュアル・特技発動確率）。

        :param list[Episode] episodes: エピソードリスト
        :return: 楽曲タイプ一致効果
        :rtype: np.ndarray
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
                        # :todo: ちゃんと実装しろ！
                        pass

            return np.zeros((len(AppealRow), len(episodes)))

        lstype = self._music.song.type  # ライブの楽曲タイプ
        np3d = np.zeros((3, len(AppealRow), len(episodes)))

        # 通常の楽曲タイプ一致
        np3d[0] = basematch(lstype, episodes)

        # ドミナント・デュエットのタイプ一致（センターあるいは、ブレスによる全員のセンター効果発動）
        buff = Calculator._buffs.get(episodes[0].buff) if episodes else Buff()
        np3d[1] = typematch(buff, episodes)

        # ドミナント・デュエットのタイプ一致（ゲストあるいは、ブレスによる全員のセンター効果発動）
        if len(episodes) == 6:
            buff = Calculator._buffs.get(episodes[5].buff)
            np3d[2] = typematch(buff, episodes)

        return np3d.max(axis=0)

    def _centerbuff(self, episodes: list[Episode], position: int = 0) -> np.ndarray:
        """
        センター効果（ボーカル・ダンス・ビジュアル・ライフ・特技発動率・特技継続期間）。

        :param list[Episode] episodes: エピソードリスト
        :param int position: センター効果を発動するメンバーの立ち位置。
        :return: センター効果データ配列
        :rtype: np.ndarray
        """

        context = BuffContext(
            on_resonance=self._resonance,
            position=position,
            buff=Calculator._buffs.get(episodes[position].buff),
            livesong_type=self._music.song.type,
            idol_typeset={episode.type for episode in episodes},
            dominant_typeset={episode.dominant for episode in episodes},
            skill_classset={episode.skill_class for episode in episodes},
            idol_typelist=[episode.type for episode in episodes],
            dominant_typelist=[episode.dominant for episode in episodes],
            episode_list=episodes,
            buff_list=[Calculator._buffs.get(episode.buff) for episode in episodes],
        )

        if episodes[position].buff_class in buff_funcname:
            # アピール値の計算に必要、かつ実装済みのセンター効果
            result = buff_funcname[episodes[position].buff_class](context)
            self._resonance = context.on_resonance

        else:
            result = np.zeros((len(AppealRow), len(episodes)))
            LibsAppealLogger.error(f"{episodes[position].buff_class}は、未実装です。")

        LibsAppealLogger.debug(f"{','.join(str(result).splitlines())}")
        return result


if __name__ == "__main__":
    print(__file__)
