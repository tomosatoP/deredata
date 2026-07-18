"""
アピールを計算するモジュール。

エピソードのアピール、サポートメンバーのアピール、ユニットメンバーのアピールを計算する。
    * アピールには、ボーカル、ダンス、ビジュアル、ライフ、特技発動率、特技継続期間がある。
    * ボーカル、ダンス、ビジュアル、ライフの値は、整数に切り上げられる。
    * ユニットメンバーにゲストがいる場合、ゲストのセンター効果も加えられる。

エピソードのアピールの計算式
    :math:`(基礎値+ポテンシャル補正)\\times(1.00+楽曲タイプ一致効果+ルーム効果+センター効果)`

サポートメンバーのアピールの計算式
    :math:`(基礎値+ポテンシャル補正)\\times(1.00+楽曲タイプ一致効果)`

ユニットメンバーのアピールの計算式
    :math:`(基礎値+ポテンシャル補正)\\times(1.00+楽曲タイプ一致効果+ルーム効果+センター効果)`
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
from deredata.libs.simulate.centerbuff import bonus_and_resonance

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
    :param Skill skill: 対象メンバーのエピソードの特技。
    :param SongType song_type: ライブ楽曲の楽曲タイプ。
    :param list[Episode] episodes: ユニットメンバーのエピソードリスト
    :param bool resonance: レゾナンスが有効かどうか。
    """

    episode: Episode = Episode()
    idol: Idol = Idol()
    skill: Skill = Skill()
    song_type: SongType = SongType.ALL
    episodes: list[Episode] = field(default_factory=list)
    resonance: bool = False


def base_value(context: BonusContext) -> np.ndarray:
    """
    アピールの基礎値。

    特技発動確率および、特技継続期間の計算式: :math:`基礎値\\times(1.00+\\dfrac{特技LV-1.00}{18.00})`

    上記以外のアピールには、エピソードの基礎値を用いる。

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

    アイドルのポテンシャルに応じたボーナスをエピソードに与える。

    対象のアピールは、ボーカル、ダンス、ビジュアル、ライフ、特技発動率。

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

    楽曲タイプとアイドルタイプが一致するエピソードに *30%* のボーナスを与える。
    楽曲タイプとドミナントアイドルタイプが一致するエピソードに *30%* のボーナスを与える。
    センター効果「ドミナント・デュエット」が有効な場合、
    アイドル（楽曲）タイプが一致するエピソードに *30%* のボーナスを与える。

    対象のアピールは、ボーカル、ダンス、ビジュアル、特技発動率。

    :param EpisodeContext context: エピソードコンテキスト。

    :return: アピールの楽曲タイプ一致効果。
    :rtype: np.ndarray
    """

    def songtypematch(type: IdolType, song_type: SongType) -> bool:
        match [type, song_type]:
            case [x, SongType.ALL]:  # noqa: F841
                return True
            case [IdolType(itype), SongType(stype)]:
                return True if itype.name == stype.name else False
            case _:
                return False

    def songtypematch_bonus(type: IdolType, song_type: SongType) -> np.ndarray:
        """楽曲タイプ一致ボーナス。"""
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
        """ドミナント・デュエット用タイプ一致ボーナス。"""
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

    def dominant_duet_typematch(buff: Buff, episode: Episode, song_type: SongType) -> np.ndarray:
        """ドミナント・デュエット。"""
        if buff.buff.startswith("ドミナント・デュエット"):
            for buffpart in buff.buffparts:
                if buffpart.appeal == AppealType.TYPEMATCH and buff.music.name == song_type.name:
                    return idoltypematch_bonus(episode.type, buffpart.member)
        return np.zeros((len(AppealIndices),))

    buffs: list[Buff] = [_buffs.get(episode.buff) for episode in context.episodes]
    result: np.ndarray = np.zeros((8, len(AppealIndices)))

    # 楽曲タイプ一致効果（センター効果「ドミナント・デュエット」のタイプ一致以外）。
    result[7] = songtypematch_bonus(context.episode.type, context.song_type)
    result[6] = songtypematch_bonus(context.episode.dominant, context.song_type)

    # センター効果「ドミナント・デュエット」のタイプ一致効果：サポートメンバーの場合。
    if not buffs:
        result[0] = dominant_duet_typematch(_buffs.get(context.episode.buff), context.episode, context.song_type)

    # センター効果「ドミナント・デュエット」のタイプ一致効果：ユニットメンバーの場合。
    if buffs:
        result[0] = dominant_duet_typematch(buffs[0], context.episode, context.song_type)

    if len(buffs) == 6:
        result[5] = dominant_duet_typematch(buffs[5], context.episode, context.song_type)

    if buffs and buffs[0].buff.startswith("シンデレラブレス"):
        # センターのセンター効果が、シンデレラブレスの場合。
        for i in [1, 2, 3, 4]:
            result[i] = dominant_duet_typematch(buffs[i], context.episode, context.song_type)

    if len(buffs) == 6 and buffs[5].buff.startswith("シンデレラブレス"):
        # ゲストのセンター効果が、シンデレラブレスの場合。
        for i in [1, 2, 3, 4]:
            result[i] = dominant_duet_typematch(buffs[i], context.episode, context.song_type)

    return result.max(axis=0)


def roombuff_bonus(context: BonusContext) -> np.ndarray:
    """
    アピールのルーム効果ボーナス。

    *10%* のボーナスを与える。

    対象のアピールは、ボーカル、ダンス、ビジュアル。

    :param BonusConext context: エピソードコンテキスト。

    :return: アピールのルーム効果。
    :rtype: np.ndarray
    """

    return np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])


def centerbuff_bonus(context: BonusContext, number: int) -> np.ndarray:
    """
    アピールのセンター効果ボーナス。

    センター効果に応じたボーナスを与える。

    :param BonusConext context: エピソードコンテキスト。
    :param int number: 評価するセンター効果を持っているメンバーの立ち位置。

    :return: アピールのセンター効果。
    :rtype: np.ndarray
    """

    result = bonus_and_resonance(
        episode=context.episode,
        buff=_buffs.get(context.episodes[number].buff),
        episodes=context.episodes,
        song_type=context.song_type,
    )

    context.resonance = True if result[1] or context.resonance else False
    return result[0]


def boothbuff_bonus(context: BonusContext) -> np.ndarray:
    """
    アピールのブース効果ボーナス。

    ブース効果に応じたボーナスを与える。

    :param BonusConext context: エピソードコンテキスト。

    :return: アピールのブース効果。
    :rtype: np.ndarray

    :todo: 未着手なので、ZERO を返す。
    """

    return np.zeros((len(AppealIndices),))


def appeal_episode(
    episode: Episode,
    episodes: list[Episode],
    music: Music,
    boothtype: BoothIndices = BoothIndices.NA,
) -> list[int | float]:
    """
    エピソードのアピール。

    :param Episode episode: 対象のエピソード。
    :param list[Episode] episodes: ユニットメンバーのエピソードリスト。ゲスト有は、長さ6。ゲスト無しは、長さ5。
    :param Music music: ライブの楽曲。
    :param BoothIndices boothtype: ライブカーニバルのブース効果。初期値は、非該当。

    :return: エピソードのアピールの値リスト。
    :rtype: list[int | float]
    """

    def formula(bonuses: list[np.ndarray]) -> np.ndarray:
        return (bonuses[0] + bonuses[1]) * (1.00 + np.sum(bonuses[2:], axis=0))

    def tolist(appeal_bonuses: np.ndarray) -> list[int | float]:

        return [
            ceil(appeal_bonuses[AppealIndices.VOCAL]),
            ceil(appeal_bonuses[AppealIndices.DANCE]),
            ceil(appeal_bonuses[AppealIndices.VISUAL]),
            ceil(appeal_bonuses[AppealIndices.LIFE]),
            float(appeal_bonuses[AppealIndices.PROBABILITY]),
            float(appeal_bonuses[AppealIndices.DURATION]),
        ]

    context = BonusContext(
        episode=episode,
        idol=_idols.get(episode.ruby),
        skill=_skills.get(episode.skill),
        song_type=music.song.type,
        episodes=episodes,
    )

    match [boothtype, len(episodes)]:
        case [BoothIndices.NA, 6]:
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
            )

        case [BoothIndices.NA, 5]:
            return tolist(
                formula(
                    bonuses=[
                        base_value(context),
                        potential_bonus(context),
                        musicbuff_bonus(context),
                        roombuff_bonus(context),
                        centerbuff_bonus(context, 0),
                    ]
                )
            )

        case _:
            return tolist(np.zeros((len(AppealIndices),)))


def appeal_support_member(support: Episode, music: Music) -> list[int]:
    """
    サポートメンバーエピソードのアピール。

    :param Episode support: サポートメンバーエピソード。
    :param Music music: ライブの楽曲。

    :return: サポートメンバーエピソードのアピールの値リスト。
    :rtype: list[int]
    """

    def formula(bonuses: list[np.ndarray]) -> np.ndarray:
        return (bonuses[0] + bonuses[1]) * (1.00 + np.sum(bonuses[2:], axis=0))

    def tolist(appeal_bonuses: np.ndarray) -> list[int]:

        return [
            ceil(0.5 * appeal_bonuses[AppealIndices.VOCAL]),
            ceil(0.5 * appeal_bonuses[AppealIndices.DANCE]),
            ceil(0.5 * appeal_bonuses[AppealIndices.VISUAL]),
        ]

    context = BonusContext(
        episode=support,
        idol=_idols.get(support.ruby),
        skill=_skills.get(support.skill),
        song_type=music.song.type,
    )

    return tolist(formula(bonuses=[base_value(context), potential_bonus(context), musicbuff_bonus(context)]))


def appeal_unit(
    episodes: list[Episode],
    music: Music = Music(),
    boothtype: BoothIndices = BoothIndices.NA,
) -> tuple[list[list[int | float]], bool]:
    """
    ユニットのアピール。

    :param list[Episode] episodes: ユニットメンバーのエピソードリスト。ゲスト有は、長さ6。ゲスト無しは、長さ5。
    :param Music music: ライブの楽曲。
    :param BoothIndices boothtype: ライブカーニバルのブース効果。初期値は、非該当。

    :return: エピソードリスト✕アピールの値リスト、レゾナンスが有効かどうか。
    :rtype: tuple[list[list[int | float]], bool]
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

    result: list = list()
    resonace: bool = False
    match [boothtype, len(episodes)]:
        case [BoothIndices.NA, 6]:
            for i, episode in enumerate(episodes):
                context = BonusContext(
                    episode=episode,
                    idol=_idols.get(episode.ruby),
                    skill=_skills.get(episode.skill),
                    song_type=music.song.type,
                    episodes=episodes,
                    resonance=False,
                )
                result.append(
                    tolist(
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
                    )
                )
                resonace = True if context.resonance or resonace else False
            return result, resonace

        case [BoothIndices.NA, 5]:
            for i, episode in enumerate(episodes):
                context = BonusContext(
                    episode=episode,
                    idol=_idols.get(episode.ruby),
                    skill=_skills.get(episode.skill),
                    song_type=music.song.type,
                    episodes=episodes,
                    resonance=False,
                )
                result.append(
                    tolist(
                        formula(
                            bonuses=[
                                base_value(context),
                                potential_bonus(context),
                                musicbuff_bonus(context),
                                roombuff_bonus(context),
                                centerbuff_bonus(context, 0),
                            ]
                        )
                    )
                )
                resonace = True if context.resonance or resonace else False
            return result, resonace

        case _:
            return tolist(np.zeros((len(AppealIndices),))), False


if __name__ == "__main__":
    print(__file__)
