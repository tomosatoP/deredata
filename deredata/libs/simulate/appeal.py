"""
アピールを計算するモジュール。
"""

import numpy as np
from math import ceil
from dataclasses import dataclass, field

from deredata.libs.database.musics import SongType, Music
from deredata.libs.database.enumerations import IdolType
from deredata.libs.database.idols import Idol, Idols
from deredata.libs.database.episodes import Episode
from deredata.libs.database.buffs import Buff, Buffs, AppealType
from deredata.libs.database.skills import Skill, Skills, duration_value, probability_value
from deredata.libs.database.potentials import Potentials

from deredata.libs.simulate.enumerations import AppealIndices, BoothIndices
from deredata.libs.simulate.centerbuff import bonus

from kivy.logger import Logger as LibsAppealLogger

_idols: Idols = Idols()
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

    :param Episode episode: 対象メンバーのエピソード
    :param Idol idol: 対象メンバーのアイドル情報
    :param Buff buff: 対象メンバーのエピソードのセンター効果。
    :param Skill skill: 対象メンバーのエピソードの特技。
    :param SongType song_type: ライブ楽曲の楽曲タイプ。
    :param list[Episode] episodes: ユニットメンバーのエピソードリスト
    :param bool on_resonance: レゾナンスが有効かどうか。
    """

    episode: Episode = Episode()
    idol: Idol = Idol()
    buff: Buff = Buff()
    skill: Skill = Skill()
    song_type: SongType = SongType.ALL
    episodes: list[Episode] = field(default_factory=list)
    on_resonance: bool = False


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

    def songtypematch(type: IdolType, matchtype: SongType) -> bool:
        match [type, matchtype]:
            case [x, SongType.ALL]:  # noqa: F841
                return True
            case [IdolType(itype), SongType(stype)]:
                return True if itype.name == stype.name else False
            case _:
                return False

    def songtypematch_bonus(type: IdolType, song_type: SongType) -> np.ndarray:
        return np.array(
            [
                0.3 if songtypematch(type, song_type) else 0.0,
                0.3 if songtypematch(type, song_type) else 0.0,
                0.3 if songtypematch(type, song_type) else 0.0,
                0.0,
                0.3 if songtypematch(type, song_type) else 0.0,
                0.0,
            ]
        )

    def idoltypematch_bonus(type: IdolType, idol_type: IdolType) -> np.ndarray:
        return np.array(
            [
                0.3 if type == idol_type else 0.0,
                0.3 if type == idol_type else 0.0,
                0.3 if type == idol_type else 0.0,
                0.0,
                0.3 if type == idol_type else 0.0,
                0.0,
            ]
        )

    buffs: list[Buff] = [_buffs.get(episode.buff) for episode in context.episodes]
    result: np.ndarray = np.zeros((7, len(AppealIndices)))

    # ドミナントアイドルタイプ以外の場合。
    result[6] = songtypematch_bonus(context.episode.type, context.song_type)

    if buffs[0].buff.startswith("ドミナント・デュエット"):
        # センターのセンター効果が、ドミナント・デュエットの場合。
        for buffpart in buffs[0].buffparts:
            if buffpart.appeal == AppealType.TYPEMATCH and buffs[0].music.name == context.song_type.name:
                result[0] = idoltypematch_bonus(context.episode.type, buffpart.member)

    if buffs[5].buff.startswith("ドミナント・デュエット"):
        # ゲストのセンター効果が、ドミナント・デュエットの場合。
        for buffpart in buffs[5].buffparts:
            if buffpart.appeal == AppealType.TYPEMATCH and buffs[5].music.name == context.song_type.name:
                result[5] = idoltypematch_bonus(context.episode.type, buffpart.member)

    if any([buffs[0].buff.startswith("シンデレラブレス"), buffs[5].buff.startswith("シンデレラブレス")]):
        # センターのセンター効果が、シンデレラブレスの場合。
        for i in [1, 2, 3, 4]:
            if buffs[i].buff.startswith("ドミナント・デュエット"):
                # センター効果が、ドミナント・デュエットの場合。
                for buffpart in buffs[i].buffparts:
                    if buffpart.appeal == AppealType.TYPEMATCH and buffs[i].music.name == context.song_type.name:
                        result[i] = idoltypematch_bonus(context.episode.type, buffpart.member)

    return result.max(axis=0)


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

    result = bonus(
        episode=context.episode,
        buff=_buffs.get(context.episodes[number].buff),
        episodes=context.episodes,
        song_type=context.song_type,
    )

    context.on_resonance = True if result[1] or context.on_resonance else False
    return result[0]


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
) -> tuple[list, bool]:
    """
    アピール。

    :param int position: ライブの立ち位置。センター(0)/左隣り(1)/右隣り(2)/左端(3)/右端(4)/ゲスト(5)
    :param list[Episode] episodes: ユニットメンバーのエピソードリスト。
    :param Music music: ライブの楽曲。
    :param bool support: **False** は、ユニットメンバー（初期値）。**True** は、サポートメンバー。
    :param BoothIndices boothtype: ライブカーニバルのブース効果。初期値は、非該当。

    :return: アピールの値リスト、レゾナンスが有効かどうか。
    :rtype: tuple[list, bool]
    """

    def formula(bonuses: list[np.ndarray]) -> np.ndarray:
        return (bonuses[0] + bonuses[1]) * (1.00 + np.sum(bonuses[2:], axis=0))

    def tolist(appeal_bonuses: np.ndarray, support: bool = False) -> list:

        if support:
            return [
                ceil(0.5 * appeal_bonuses[AppealIndices.VOCAL]),
                ceil(0.5 * appeal_bonuses[AppealIndices.DANCE]),
                ceil(0.5 * appeal_bonuses[AppealIndices.VISUAL]),
            ]

        else:
            return [
                ceil(appeal_bonuses[AppealIndices.VOCAL]),
                ceil(appeal_bonuses[AppealIndices.DANCE]),
                ceil(appeal_bonuses[AppealIndices.VISUAL]),
                ceil(appeal_bonuses[AppealIndices.LIFE]),
                float(appeal_bonuses[AppealIndices.PROBABILITY]),
                float(appeal_bonuses[AppealIndices.DURATION]),
            ]

    context = BonusContext(
        episode=episodes[position],
        idol=_idols.get(episodes[position].ruby),
        buff=_buffs.get(episodes[position].buff),
        skill=_skills.get(episodes[position].skill),
        song_type=music.song.type,
        episodes=[episodes[i] if len(episodes) > i else Episode() for i in range(6)],
        on_resonance=False,
    )

    print(f"基礎値: {base_value(context)}")
    print(f"ポテンシャル補正: {potential_bonus(context)}")
    print(f"楽曲タイプ一致補正: {musicbuff_bonus(context)}")
    print(f"ルーム効果: {roombuff_bonus(context)}")
    print(f"センター効果（センター）: {centerbuff_bonus(context, 0)}")
    print(f"センター効果（ゲスト）: {centerbuff_bonus(context, 5)}")

    match [boothtype, support]:
        case [BoothIndices.NA, False]:
            return tolist(
                formula(
                    bonuses=[
                        base_value(context),
                        potential_bonus(context),
                        musicbuff_bonus(context),
                        roombuff_bonus(context),
                        centerbuff_bonus(context, 0),
                        centerbuff_bonus(context, 5),
                    ]
                )
            ), context.on_resonance

        case [BoothIndices.NA, True]:
            return tolist(
                formula(
                    bonuses=[
                        base_value(context),
                        potential_bonus(context),
                        musicbuff_bonus(context),
                    ]
                ),
                support=True,
            ), False

        case _:
            return tolist(np.zeros((len(AppealIndices),))), False


if __name__ == "__main__":
    print(__file__)
