"""
列挙クラスの一覧のモジュール。
"""

from enum import StrEnum, IntEnum


class AppealIndices(IntEnum):
    """
    エピソード名を除くアピールタイプの列挙クラス。ボーナス配列の添え字に相当する。

    :VOCAL: 0: ボーカル
    :DANCE: 1: ダンス
    :VISUAL: 2: ビジュアル
    :LIFE: 3: ライフ
    :PROBABILITY: 4: 特技発動確率
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


if __name__ == "__main__":
    print(__file__)
