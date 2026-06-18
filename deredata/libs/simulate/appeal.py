"""
アピールを計算するモジュール。
"""

import numpy as np
from math import ceil
from enum import IntEnum
from typing import Any, Callable
from dataclasses import dataclass, field
from functools import singledispatch

from deredata.libs.database.musics import SongType, Music
from deredata.libs.database.enumerations import IdolType, DominantType, MusicType, UnitType
from deredata.libs.database.idols import Idol, Idols
from deredata.libs.database.episodes import Episode, Episodes
from deredata.libs.database.units import Unit
from deredata.libs.database.buffs import BuffPart, Buff, Buffs, AppealType
from deredata.libs.database.skills import Skill, Skills, duration_value, probability_value
from deredata.libs.database.potentials import Potentials

from deredata.libs.simulate.enumerations import AppealIndices, BoothIndices
from deredata.libs.simulate.centerbuff import bonus

from kivy.logger import Logger as LibsAppealLogger

_idols: Idols = Idols()
_episodes: Episodes = Episodes()
_buffs: Buffs = Buffs()
_skills: Skills = Skills()
_potentials: Potentials = Potentials()


class AppealError(Exception):
    """appealモジュールのエラーハンドラ。"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsAppealLogger.error(f"AppealError: {args}")


@dataclass
class BonusContext:
    """
    アピールボーナスのコンテキストのデータクラス。

    :param bool support: サポートメンバーかどうか（初期値 *False* は、非サポートメンバー）。
    :param int position: ライブの立ち位置。
    :param Episode episode: 立ち位置 *positon* のエピソード
    :param Idol idol: 立ち位置 *positon* のアイドル情報
    :param Buff buff: 立ち位置 *positon* のエピソードのセンター効果。
    :param Skill skill: 立ち位置 *positon* のエピソードの特技。
    :param SongType songtype: ライブ楽曲の楽曲タイプ。
    """

    support: bool = False
    position: int = 0
    episode: Episode = Episode()
    idol: Idol = Idol()
    buff: Buff = Buff()
    skill: Skill = Skill()
    songtype: SongType = SongType.ALL
    idoltypes_set: set[IdolType] = field(default_factory=set)
    dominanttypes_set: set[DominantType] = field(default_factory=set)
    skillclasses_set: set[str] = field(default_factory=set)
    idoltypes_list: list[IdolType] = field(default_factory=list)
    dominanttypes_list: list[DominantType] = field(default_factory=list)
    episodes_list: list[Episode] = field(default_factory=list)
    buffs_list: list[Buff] = field(default_factory=list)


@singledispatch
def songtypematch(type: Any, songtype: SongType) -> bool:
    """
    タイプと楽曲タイプの一致を判定する。

    引数 *type* と 引数 *songtype* のタイプが一致する場合に、``True`` を返す。
    それ以外は、 ``False`` を返す。

    :param Any type: アイドルタイプ（*IdolType*）／ドミナントアイドルタイプ（*DominantType*）。
    :param SongType songtype: 楽曲タイプ。

    :return: タイプが一致する時は **True** 、一致しない時は **False** を返す。
    :rtype: bool
    """

    LibsAppealLogger.error(f"appeal.songtypematch: {type}が、不正です。")
    return False


@songtypematch.register(IdolType)
def _(type: IdolType, songtype: SongType) -> bool:

    match [type, songtype]:
        case [x, SongType.ALL]:  # noqa: F841
            return True

        case [IdolType(itype), SongType(stype)]:
            return True if itype.name == stype.name else False

        case _:
            LibsAppealLogger.error(f"appeal.songtypematch: {type},{songtype} が、不正です。")
            return False


@songtypematch.register(DominantType)
def _(type: DominantType, songtype: SongType) -> bool:
    match [type, songtype]:
        case [x, SongType.ALL]:  # noqa: F841
            return True

        case [DominantType(dtype), SongType(stype)]:
            return True if dtype.name == stype.name else False

        case _:
            LibsAppealLogger.error(f"appeal.songtypematch: {type},{songtype} が、不正です。")
            return False


def base_value(context: BonusContext) -> np.ndarray:
    """
    アピールの基礎値。

    特技発動確率および、特技継続期間の計算式: :math:`基礎値\\times(1.00+\\dfrac{特技LV-1.00}{18.00})`

    :param EpisodeContext context: エピソードコンテキスト。

    :return: アピールの基礎値。
    :rtype: np.ndarray
    """

    return np.array(
        [
            context.episode.vocal,
            context.episode.dance,
            context.episode.visual,
            context.episode.life,
            probability_value(context.skill.probability) * (1.0 + (context.episode.skill_level - 1.0) / 18.0),
            duration_value(context.skill.duration) * (1.0 + (context.episode.skill_level - 1.0) / 18.0),
        ]
    )


def potential_bonus(context: BonusContext) -> np.ndarray:
    """
    アピールのポテンシャル補正ボーナス。

    .. csv-table:: ポテンシャル補正
        :header-rows: 1
        :stub-columns: 1
        :widths: 1, 6

        "項目", "内容"
        "対象", "ボーカルアピール、ダンスアピール、ビジュアルアピール、ライフ、特技発動確率"

    :param EpisodeContext context: エピソードコンテキスト。

    :return: アピールのポテンシャル補正値。
    :rtype: np.ndarray
    """

    return np.array(
        [
            _potentials.value(type="ボーカル", rare=context.episode.rare, level=context.idol.vocal),
            _potentials.value(type="ダンス", rare=context.episode.rare, level=context.idol.dance),
            _potentials.value(type="ビジュアル", rare=context.episode.rare, level=context.idol.visual),
            _potentials.value(type="ライフ", rare=context.episode.rare, level=context.idol.life),
            _potentials.value(type="特技発動率", rare=context.episode.rare, level=context.idol.skill),
            0.0,
        ]
    )


def musicbuff_bonus(context: BonusContext) -> np.ndarray:
    """
    アピールの楽曲タイプ一致効果ボーナス。

    .. csv-table:: 楽曲タイプ一致効果
        :header-rows: 1
        :stub-columns: 1
        :widths: 1, 6

        "項目", "内容"
        "条件", "ライブの楽曲タイプとアイドルタイプが一致。"
        "条件", "センター効果「ドミナント・デュエット」有効時、ライブの楽曲タイプとドミナントアイドルタイプが一致。"
        "対象", "ボーカルアピール、ダンスアピール、ビジュアルアピール、特技発動確率。"
        "効果量", "30%"

    :param EpisodeContext context: エピソードコンテキスト。

    :return: アピールの楽曲タイプ一致効果。
    :rtype: np.ndarray
    """

    # センターのセンター効果「ドミナント・デュエット」。
    # ゲストのセンター効果「ドミナント・デュエット」。
    # シンデレラブレス有効時、メンバーのセンター効果「ドミナント・デュエット」。

    return np.array(
        [
            0.3 if songtypematch(context.episode.type, context.songtype) else 0.0,
            0.3 if songtypematch(context.episode.type, context.songtype) else 0.0,
            0.3 if songtypematch(context.episode.type, context.songtype) else 0.0,
            0.0,
            0.3 if songtypematch(context.episode.type, context.songtype) else 0.0,
            0.0,
        ]
    )


def roombuff_bonus(context: BonusContext) -> np.ndarray:
    """
    アピールのルーム効果ボーナス。

    .. csv-table:: ルーム効果
        :header-rows: 1
        :stub-columns: 1
        :widths: 1, 6

        "項目", "内容"
        "条件", "サポートメンバー以外"
        "対象", "ボーカルアピール、ダンスアピール、ビジュアルアピール"
        "効果量", "10%"

    :param EpisodeConext context: エピソードコンテキスト。

    :return: アピールのルーム効果。
    :rtype: np.ndarray
    """

    return np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])


def centerbuff_bonus(context: BonusContext, number: int) -> np.ndarray:
    """
    アピールのセンター効果ボーナス。

    :param EpisodeConext context: エピソードコンテキスト。
    :param int number: 評価するセンター効果を持っているメンバーの立ち位置。

    :return: アピールのセンター効果。
    :rtype: np.ndarray
    """

    return bonus(
        buff=_buffs.get(context.episodes_list[number].buff) if len(context.episodes_list) >= number else Buff(),
        episodes=context.episodes_list,
        songtype=context.songtype,
    )


def boothbuff_bonus(context: BonusContext) -> np.ndarray:
    """
    アピールのブース効果ボーナス。

    :param EpisodeConext context: エピソードコンテキスト。

    :return: アピールのブース効果。
    :rtype: np.ndarray
    """

    return np.zeros((len(AppealIndices),))


def appeal(
    position: int,
    episodes: list[Episode],
    music: Music = Music(),
    support: bool = False,
    boothtype: BoothIndices = BoothIndices.NA,
) -> list:
    """
    アピール。

    :param int position: ライブの立ち位置。センター(0)/左隣り(1)/右隣り(2)/左端(3)/右端(4)/ゲスト(5)
    :param list[Episode] episodes: ユニットメンバーのエピソードリスト。
    :param Music music: ライブの楽曲。
    :param bool support: **False** は、ユニットメンバー（初期値）。**True** は、サポートメンバー。
    :param BoothIndices boothtype: ライブカーニバルのブース効果。初期値は、非該当。

    :return: アピールの値リスト。
    :rtype: list
    """

    def formula(bonuses: list[np.ndarray]) -> np.ndarray:
        return (bonuses[0] + bonuses[1]) * (1.00 + np.sum(bonuses[2:], axis=0))

    def tolist(appeal_bonuses: np.ndarray) -> list:
        return [
            ceil(appeal_bonuses[AppealIndices.VOCAL]),
            ceil(appeal_bonuses[AppealIndices.DANCE]),
            ceil(appeal_bonuses[AppealIndices.VISUAL]),
            ceil(appeal_bonuses[AppealIndices.LIFE]),
            float(appeal_bonuses[AppealIndices.PROBABILITY]),
            float(appeal_bonuses[AppealIndices.DURATION]),
        ]

    context = BonusContext(
        support=support,
        position=position,
        episode=episodes[position],
        idol=_idols.get(episodes[position].ruby),
        buff=_buffs.get(episodes[position].buff),
        skill=_skills.get(episodes[position].skill),
        songtype=music.song.type,
        episodes_list=episodes,
    )

    print(f"基礎値: {base_value(context)}")
    print(f"ポテンシャル補正: {potential_bonus(context)}")
    print(f"楽曲タイプ一致補正: {musicbuff_bonus(context)}")
    print(f"ルーム効果: {roombuff_bonus(context)}")
    print(f"センター効果: {centerbuff_bonus(context, 0)}")
    print(f"センター効果: {centerbuff_bonus(context, 5)}")

    match [boothtype, support]:
        case [BoothIndices.NA, False]:
            return tolist(
                formula(
                    [
                        base_value(context),
                        potential_bonus(context),
                        musicbuff_bonus(context),
                        roombuff_bonus(context),
                        centerbuff_bonus(context, 0),
                        centerbuff_bonus(context, 5),
                    ]
                )
            )

        case [BoothIndices.NA, True]:
            return tolist(
                formula(
                    [
                        base_value(context),
                        potential_bonus(context),
                        musicbuff_bonus(context),
                    ]
                )
            )

        case _:
            return tolist(np.zeros((len(AppealIndices),)))


if __name__ == "__main__":
    print(__file__)
