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
    - センター効果・ワールドレべルの実装（フェイスオープン：60秒前後で2つのアピール）。
    - 楽曲タイプ一致の実装修正：シンデレラブレスから他のセンター効果を呼び出し時の対応。完了
"""

from deredata.libs.database.musics import Music
from deredata.libs.database.idols import Idols
from deredata.libs.database.episodes import Episode, Episodes
from deredata.libs.database.units import Unit
from deredata.libs.database.buffs import Buffs
from deredata.libs.database.skills import Skills
from deredata.libs.database.potentials import Potentials

from deredata.libs.simulate.enumerations import AppealIndices, BoothIndices
from deredata.libs.simulate.appeal import appeal_support_member, appeal_unit

from kivy.logger import Logger as LibsBackstageLogger


class BackstageError(Exception):
    """backstageモジュールのエラーハンドラ。"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsBackstageLogger.error(f"BackstageError: {args}")


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
            [episode.episode for episode in self._unit_episodes],
            [appeal[AppealIndices.VOCAL] for appeal in self._unit],
            [appeal[AppealIndices.DANCE] for appeal in self._unit],
            [appeal[AppealIndices.VISUAL] for appeal in self._unit],
            [appeal[AppealIndices.LIFE] for appeal in self._unit],
            [appeal[AppealIndices.PROBABILITY] for appeal in self._unit],
            [appeal[AppealIndices.DURATION] for appeal in self._unit],
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
            [appeal[AppealIndices.VOCAL] for appeal in self._support],
            [appeal[AppealIndices.DANCE] for appeal in self._support],
            [appeal[AppealIndices.VISUAL] for appeal in self._support],
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

        # ゲストを含むユニットメンバーのアピール
        self._unit_episodes: list[Episode] = [
            self.__class__._episodes.get(episode) for episode in unit.positions.list() if isinstance(episode, str)
        ]

        self._unit: list
        self._unit, self._resonance = appeal_unit(self._unit_episodes, self._music)

        # サポートメンバーのアピール
        self._support_episodes: list[Episode] = self._select_support_episodes(unit)
        self._support: list = [appeal_support_member(episode, self._music) for episode in self._support_episodes]

        self._log()
        LibsBackstageLogger.info(f"{self.__class__.__name__}.run: アピール値計算完了。")

    def _select_support_episodes(self, unit: Unit) -> list[Episode]:
        """
        サポートメンバー（エピソード）の選出を行う。

        ポテンシャル補正と楽曲タイプ一致効果を適用したアピール値（ボーカル・ダンス・ビジュアル）のトップ10をサポートメンバーとする。
        スターランク分の重複を許容し、ユニットメンバーとの重複分は差し引く。

        :param list[str] UnitEpisodes: ゲストを含むユニットメンバーのエピソード名リスト
        :return: サポートメンバーのエピソードリスト
        :rtype: list[Episode]
        """

        # 全エピソードのアピール値合計を計算し、リスト化（未所有：スターランクが ZERO）を除く）。
        all_episodes = sorted({episode for episode in self.__class__._episodes.gets() if episode.star_rank > 0})
        all_appeals = [sum(appeal_support_member(episode, self._music)) for episode in all_episodes]

        # アピール値合計の高い順にエピソードをリスト化し、トップ10を選出。
        # スターランク分の重複を許容し、ユニットメンバーとの重複分は差し引く。
        all_appeals_episodes = [(appeal, episode) for appeal, episode in zip(all_appeals, all_episodes)]
        support_episodes: list[Episode] = list()
        for appeal, episode in sorted(all_appeals_episodes, reverse=True):
            for _ in range(episode.star_rank - 1 if episode in unit.positions.list() else episode.star_rank):
                support_episodes.append(episode)
                if len(support_episodes) == 10:
                    break
            else:
                continue
            break

        return support_episodes


if __name__ == "__main__":
    print(__file__)
