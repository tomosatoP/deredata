"""
アイドルエピソードを絞り込み検索するモジュール。

アイドルエピソードを、所有・非所有、アイドルタイプ、レア度、特技発動間隔、センター効果分類、特技分類で絞り込み検索する。
"""

from typing import Any
import itertools

from deredata.libs.database.idols import Idols
from deredata.libs.database.episodes import Episode, Episodes
from deredata.libs.database.buffs import Buffs
from deredata.libs.database.skills import Skills

from kivy.input.motionevent import MotionEvent
from kivy.uix.recycleview import RecycleView
from kivy.factory import Factory
from kivy.logger import Logger as BuffSkillLogger


class EpisodeInfoViewclass(Factory.RecycleDataViewBehavior, Factory.BoxLayout):
    """
    各種の絞り込みの結果得られたエピソードのエピソード情報を表示するウィジット。
    """

    index: int | None = None
    selected = Factory.BooleanProperty(None)
    selectable = Factory.BooleanProperty(True)

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)
        self._idols: Idols = Idols()

    def refresh_view_attrs(self, rv: RecycleView, index: int, data: dict) -> Any:
        """
        データ、ビューの初期化時、インデックスを付け直す（class ``RecycleAdapter`` が呼び出す）。

        :param RecycleView rv: ビューの親リサイクルビュー。
        :param int index: ビューのインデックス。
        :param dict data: ビューに設定されるデータ。

        :return: 継承元クラスのメソッドを呼び出す。
        :rtype: Any
        """

        self.episode: Episode = data["episodeinfo"]
        self.index = index

        self.strepisode.text = self.episode.episode
        self.buff.text = self.episode.buff_class
        self.skill.text = self.episode.skill_class
        self.vocal_potential.text = str(self._idols.get(self.episode.ruby).vocal)
        self.dance_potential.text = str(self._idols.get(self.episode.ruby).dance)
        self.visual_potential.text = str(self._idols.get(self.episode.ruby).visual)
        self.life_potential.text = str(self._idols.get(self.episode.ruby).life)
        self.skill_potential.text = str(self._idols.get(self.episode.ruby).skill)

        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch: MotionEvent) -> Any:
        """
        ビューがタッチイベントを受け取る。

        選択可能である（``selectable`` が **True**）とき、
        選択状態を反転することを親レイアウトに伝播する。

        :param MotionEvent touch: 受け取ったタッチイベント。

        :return: 親レイアウトに選択状態の反転を要請する。
        :rtype: Any
        """

        if super().on_touch_down(touch):
            return True

        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv: RecycleView, index: int, is_selected: bool) -> None:
        """
        ビューの選択変更時、ビューに反映する。

        :param RecycleView rv: ビューの親リサイクルビュー。
        :param int index: ビューのインデックス。
        :param bool is_selected: ``True`` の場合は、ビューは選択された。``False`` の場合は、選択されなかった。
        """

        self.selected = is_selected


class EpisodeSelector(Factory.BoxLayout):
    """
    メンバーの候補を各種条件で絞り込み、アイドルのエピソードを選択するウィジット。

    :絞り込みの条件:
      所有、アイドルタイプ、レア度、特技発動間隔
      センター効果（センター効果分類説明別）
      特技（特技分類別）
    """

    framework = Factory.ObjectProperty(None)
    buffselector = Factory.ObjectProperty(None)
    skillselector = Factory.ObjectProperty(None)
    episodeselector = Factory.ObjectProperty(None)

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        self._skills: Skills = Skills()
        self._buffs: Buffs = Buffs()
        self._episodes: Episodes = Episodes()

        # 所有、アイドルタイプ、レア度、特技発動間隔で絞り込み
        self.framework.clear_widgets()

        self.hold = Factory.StrToggleButton(text="所有のみ", state="down")
        self.hold.bind(state=lambda instance, values: self.update())
        self.framework.add_widget(self.hold)

        self.framework.add_widget(Factory.StrView(text="タイプ"))
        for idoltype in ["CUTE", "COOL", "PASSION"]:
            togglebutton = Factory.StrToggleButton(text=idoltype, state="normal")
            togglebutton.bind(state=lambda instance, values: self.update())
            self.framework.add_widget(togglebutton)

        self.framework.add_widget(Factory.StrView(text="レア度"))
        for rare in ["USRPLUS", "SSRPLUS", "SRPLUS", "RPLUS", "NPLUS"]:
            togglebutton = Factory.StrToggleButton(text=rare, state="normal")
            togglebutton.bind(state=lambda instance, values: self.update())
            self.framework.add_widget(togglebutton)

        self.framework.add_widget(Factory.StrView(text="特技発動間隔"))
        for interval in sorted({skill.interval for skill in self._skills.gets()}, reverse=True):
            togglebutton = Factory.StrToggleButton(text=str(interval), state="normal")
            togglebutton.bind(state=lambda instance, values: self.update())
            self.framework.add_widget(togglebutton)

        # センター効果分類説明で絞り込み
        self.buffselector.clear_widgets()
        for categoryname in sorted(self._buffs.categorynames):
            togglebutton = Factory.StrToggleButton(text=categoryname, state="normal")
            togglebutton.bind(state=lambda instance, values: self.update())
            self.buffselector.add_widget(togglebutton)

        # 特技分類で絞り込み
        self.skillselector.clear_widgets()
        for category in sorted(self._skills.categories):
            togglebutton = Factory.StrToggleButton(text=category, state="normal")
            togglebutton.bind(state=lambda instance, values: self.update())
            self.skillselector.add_widget(togglebutton)

    def update(self) -> None:
        """
        各種絞り込み条件に応じたエピソードを表示する。

        - 所有、アイドルタイプ、レア度、特技発動間隔
        - センター効果分類説明
        - 特技分類
        """

        # 所有しているかどうかでエピソードを制限
        episodes_by_hold: set[Episode]
        if self.hold.state == "down":
            episodes_by_hold = {episode for episode in self._episodes.gets() if episode.star_rank > 0}
        else:
            episodes_by_hold = {episode for episode in self._episodes.gets()}

        # アイドルタイプでエピソードを制限
        types: set[str] = {
            widget.text
            for widget in self.framework.children
            if widget.text in ["CUTE", "COOL", "PASSION"] and widget.state == "down"
        }
        episodes_by_type: set[Episode] = {episode for episode in self._episodes.gets() if episode.type.name in types}

        # レア度でエピソードを制限
        rares: set[str] = {
            widget.text
            for widget in self.framework.children
            if widget.text in ["USRPLUS", "SSRPLUS", "SRPLUS", "RPLUS", "NPLUS"] and widget.state == "down"
        }
        episodes_by_rare: set[Episode] = {episode for episode in self._episodes.gets() if episode.rare.name in rares}

        # センター効果でエピソードを制限
        buffcategorynames: set[str] = {widget.text for widget in self.buffselector.children if widget.state == "down"}
        buffs: set[str] = set(
            itertools.chain.from_iterable([self._buffs.buffs_by_categoryname(name) for name in buffcategorynames])
        )
        episodes_by_buff: set[Episode] = {episode for episode in self._episodes.gets() if episode.buff_class in buffs}

        # 特技でエピソードを制限
        skillcategories: set[str] = {widget.text for widget in self.skillselector.children if widget.state == "down"}
        skills: set[str] = set(
            itertools.chain.from_iterable([self._skills.skills_by_category(category) for category in skillcategories])
        )
        episodes_by_skill: set[Episode] = {
            episode for episode in self._episodes.gets() if episode.skill_class in skills
        }

        # 特技発動間隔でエピソードを制限
        intervals: set[int] = {
            int(widget.text) for widget in self.framework.children if widget.text.isdigit() and widget.state == "down"
        }
        episodes_by_interval: set[Episode] = {
            episode for episode in self._episodes.gets() if self._skills.get(episode.skill).interval in intervals
        }

        # 選択されたエピソード
        episodes: set[Episode] = (
            episodes_by_hold
            & episodes_by_type
            & episodes_by_rare
            & (episodes_by_buff | (episodes_by_skill & episodes_by_interval))
        )

        self.episodeselector.layout_manager.clear_selection()
        self.episodeselector.data = [{"episodeinfo": episode} for episode in sorted(episodes)]

        # 選択状態の初期値が反映されない、なぜ？
        [self.episodeselector.layout_manager.select_node(i) for i in range(len(self.episodeselector.data))]

    def selected(self) -> list[Episode]:
        """
        選択されたエピソードを返す。
        """

        reslut: list[Episode] = [
            data["episodeinfo"]
            for i, data in enumerate(self.episodeselector.data)
            if i in self.episodeselector.layout_manager.selected_nodes
        ]
        return reslut


class FiveMemberUnit(Factory.Screen):
    """
    5人編成
    """

    centerposition = Factory.ObjectProperty(None)
    leftposition = Factory.ObjectProperty(None)
    rightposition = Factory.ObjectProperty(None)
    leftendposition = Factory.ObjectProperty(None)
    rightendposition = Factory.ObjectProperty(None)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.centerposition.add_widget(EpisodeSelector())
        self.leftposition.add_widget(EpisodeSelector())
        self.rightposition.add_widget(EpisodeSelector())
        self.leftendposition.add_widget(EpisodeSelector())
        self.rightendposition.add_widget(EpisodeSelector())

        BuffSkillLogger.info(f"{self.__class__.__name__}: 初期化しました。")

    def update(self) -> None:
        self.centerposition.content.update()
        self.leftposition.content.update()
        self.rightposition.content.update()
        self.leftendposition.content.update()
        self.rightendposition.content.update()

    def selected(self) -> list[Episode]:
        """
        選択されたエピソードを返す。
        """

        result: list[Episode] = []
        for position in [
            self.centerposition,
            self.leftposition,
            self.rightposition,
            self.leftendposition,
            self.rightendposition,
        ]:
            result.append(position.content.selected())

        return result


class SixMemberUnit(Factory.Screen):
    """
    6人編成
    """

    centerposition = Factory.ObjectProperty(None)
    leftposition = Factory.ObjectProperty(None)
    rightposition = Factory.ObjectProperty(None)
    leftendposition = Factory.ObjectProperty(None)
    rightendposition = Factory.ObjectProperty(None)
    guestposition = Factory.ObjectProperty(None)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.centerposition.add_widget(EpisodeSelector())
        self.leftposition.add_widget(EpisodeSelector())
        self.rightposition.add_widget(EpisodeSelector())
        self.leftendposition.add_widget(EpisodeSelector())
        self.rightendposition.add_widget(EpisodeSelector())
        self.guestposition.add_widget(EpisodeSelector())

        BuffSkillLogger.info(f"{self.__class__.__name__}: 初期化しました。")

    def update(self) -> None:
        self.centerposition.content.update()
        self.leftposition.content.update()
        self.rightposition.content.update()
        self.leftendposition.content.update()
        self.rightendposition.content.update()
        self.guestposition.content.update()

    def selected(self) -> list[Episode]:
        """
        選択されたエピソードを返す。
        """

        reslut: list[Episode] = []
        for position in [
            self.centerposition,
            self.leftposition,
            self.rightposition,
            self.leftendposition,
            self.rightendposition,
            self.guestposition,
        ]:
            reslut.append(position.content.selected())

        return reslut


class BuffSkillView(Factory.ScreenManager):
    """
    立ち位置別、各種条件でアイドルのエピソードを絞り込むウィジット。

    :立ち位置:
      センター、左隣り、右隣り、左端、右端、ゲスト
    """

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        self.add_widget(SixMemberUnit(name="wide6"))
        self.add_widget(FiveMemberUnit(name="unita"))
        self.add_widget(FiveMemberUnit(name="unitb"))
        self.add_widget(FiveMemberUnit(name="unitc"))
        self.add_widget(FiveMemberUnit(name="carnival_1"))
        self.add_widget(FiveMemberUnit(name="carnival_2"))
        self.add_widget(FiveMemberUnit(name="carnival_3"))
        self.add_widget(FiveMemberUnit(name="carnival_4"))
        self.add_widget(FiveMemberUnit(name="carnival_5"))
        self.add_widget(FiveMemberUnit(name="carnival_6"))
        self.add_widget(FiveMemberUnit(name="carnival_7"))
        self.add_widget(FiveMemberUnit(name="carnival_8"))
        self.add_widget(FiveMemberUnit(name="carnival_9"))

        self.current = "wide6"

        BuffSkillLogger.info(f"{self.__class__.__name__}: 初期化しました。")

    def close(self) -> None:
        """
        データベースの終了処理。
        """

        BuffSkillLogger.info(f"{self.__class__.__name__}: 終了します。")

    def update(self) -> None:
        """
        更新。
        """

        # self.wideguest.content.update()
        # self.widenoguest.content.update()
        # self.granda.content.update()
        # self.grandb.content.update()
        # self.grandc.content.update()
        pass

    def selected(self) -> list[Episode]:
        """
        選択されたエピソードを返す。
        """

        reslut: list[Episode] = self.current_screen.selected()
        return reslut


if __name__ == "__main__":
    print(__file__)
