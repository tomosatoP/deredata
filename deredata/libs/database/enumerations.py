"""
列挙クラスの一覧のモジュール。

:class IdolType: アイドルタイプの列挙クラス。
:class DominantType: ドミナントアイドルタイプの列挙クラス。
:class RareClass: レア度の列挙クラス。
:class MusicType: 楽曲タイプの列挙クラス。
:class GachaType: 入手枠（ガチャ＆マイスタイル）タイプの列挙クラス。
:class UnitType: ユニット編成タイプの列挙クラス。
"""

from enum import StrEnum


class IdolType(StrEnum):
    """
    アイドルタイプの列挙クラス。

    :NA: 非該当（主にプロデューサー自身のこと）
    :ALL: 全員
    :CUTE: キュートアイドル
    :COOL: クールアイドル
    :PASSION: パッションアイドル
    :HELEN: ヘレン
    :UNITS: 全ユニット
    :CUTE_OF_UNITS: 全ユニットのキュートアイドル
    :COOL_OF_UNITS: 全ユニットのクールアイドル
    :PASSION_OF_UNITS: 全ユニットのパッションアイドル
    """

    NA = "非該当"  # プロデューサー
    UNIT = "全員"
    CUTE = "キュートアイドル"
    COOL = "クールアイドル"
    PASSION = "パッションアイドル"
    HELEN = "ヘレン"
    UNITS = "全ユニット"
    CUTE_OF_UNITS = "全ユニットのキュートアイドル"
    COOL_OF_UNITS = "全ユニットのクールアイドル"
    PASSION_OF_UNITS = "全ユニットのパッションアイドル"


class DominantType(StrEnum):
    """
    ドミナントアイドルタイプの列挙クラス。

    :NA: 非該当
    :CUTE: キュートドミナントアイドル
    :COOL: クールドミナントアイドル
    :PASSION: パッションドミナントアイドル
    """

    NA = "非該当"
    CUTE = "キュートドミナントアイドル"
    COOL = "クールドミナントアイドル"
    PASSION = "パッションドミナントアイドル"


class RareClass(StrEnum):
    """
    レア度の列挙クラス。

    | N, NPLUS,
    | R, RPLUS,
    | SR, SRPLUS,
    | SSR, SSRPLUS,
    | USR, USRPLUS,
    """

    N = "ノーマル"
    NPLUS = "ノーマル＋"
    R = "レア"
    RPLUS = "レア＋"
    SR = "Ｓレア"
    SRPLUS = "Ｓレア＋"
    SSR = "ＳＳレア"
    SSRPLUS = "ＳＳレア＋"
    USR = "ＵＳレア"
    USRPLUS = "ＵＳレア＋"


class MusicType(StrEnum):
    """
    楽曲タイプの列挙クラス。

    :NA: 非該当
    :ALL: 全タイプ楽曲
    :CUTE: キュート楽曲
    :COOL: クール楽曲
    :PASSION: パッション楽曲
    """

    NA = "非該当"
    ALL = "全タイプ楽曲"
    CUTE = "キュート楽曲"
    COOL = "クール楽曲"
    PASSION = "パッション楽曲"


class GachaType(StrEnum):
    """
    入手枠（ガチャ＆マイスタイル）タイプの列挙クラス。

    :NORMAL: 恒常
    :EVENT: イベント
    :LIMIT: 限定
    :NOIR: ノワール限定
    :BRANC: ブラン限定
    :DOMINANT: ドミナント限定
    :MYSTYLE: マイスタイル
    """

    NORMAL = "恒常"
    EVENT = "イベント"
    LIMIT = "限定"
    NOIR = "ノワール限定"
    BRANC = "ブラン限定"
    DOMINANT = "ドミナント限定"
    MYSTYLE = "マイスタイル"


class UnitType(StrEnum):
    """
    ユニット編成タイプの列挙クラス。

    | NA,
    | ALL,
    | ONLY_CUTE, ONLY_COOL, ONLY_PASSION,
    | ONLY_CUTE_AND_COOL, ONLY_CUTE_AND_PASSION,
    | ONLY_COOL_AND_CUTE, ONLY_COOL_AND_PASSION,
    | ONLY_PASSION_AND_CUTE, ONLY_PASSION_AND_COOL,
    | CUTE_AND_COOL, CUTE_AND_PASSION,
    | COOL_AND_CUTE, COOL_AND_PASSION,
    | PASSION_AND_CUTE, PASSION_AND_COOL,
    | FIVE_SKILLS
    """

    NA = "非該当"
    ALL = "3タイプ全てのアイドル編成"
    ONLY_CUTE = "キュートアイドルのみ編成"
    ONLY_COOL = "クールアイドルのみ編成"
    ONLY_PASSION = "パッションアイドルのみ編成"
    ONLY_CUTE_AND_COOL = "キュートとクールのアイドルのみ編成"
    ONLY_CUTE_AND_PASSION = "キュートとパッションのアイドルのみ編成"
    ONLY_COOL_AND_CUTE = "クールとキュートのアイドルのみ編成"
    ONLY_COOL_AND_PASSION = "クールとパッションのアイドルのみ編成"
    ONLY_PASSION_AND_CUTE = "パッションとキュートのアイドルのみ編成"
    ONLY_PASSION_AND_COOL = "パッションとクールのアイドルのみ編成"
    CUTE_AND_COOL = "キュートとクールのアイドル編成"
    CUTE_AND_PASSION = "キュートとパッションのアイドル編成"
    COOL_AND_CUTE = "クールとキュートのアイドル編成"
    COOL_AND_PASSION = "クールとパッションのアイドル編成"
    PASSION_AND_CUTE = "パッションとキュートのアイドル編成"
    PASSION_AND_COOL = "パッションとクールのアイドル編成"
    FIVE_SKILLS = "5種類の特技編成"


if __name__ == "__main__":
    print(__file__)
