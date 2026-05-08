"""
モジュール。
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

    index = None
    selected = Factory.BooleanProperty(None)
    selectable = Factory.BooleanProperty(True)

    def refresh_view_attrs(self, rv: RecycleView, index: int, data: dict) -> Any:
        """
        ビューの変更時、インデックスを付け直す。

        データの変更、ビューポートの変更がビューに波及する際に、呼び出される。
        レイアウトにも波及する場合には、``refresh_view_layout`` も呼び出される。

        ``kivy.uix.recycleview.views.RecycleDataViewBehavior`` のメソッドを継承。

        :param RecycleView rv: ビューの親リサイクルビュー。
        :param int index: ビューのインデックス。
        :param dict data: ビューに表示するデータ。

        :return: 継承元クラスのメソッドを呼び出す。
        :rtype: Any
        """

        self.episode: Episode = data["episodeinfo"]
        self.index = index

        self.strepisode.text = self.episode.episode
        self.buff.text = self.episode.buff_class
        self.skill.text = self.episode.skill_class
        self.vocal_potential.text = str(BuffSkillView._idols.get(self.episode.ruby).vocal)
        self.dance_potential.text = str(BuffSkillView._idols.get(self.episode.ruby).dance)
        self.visual_potential.text = str(BuffSkillView._idols.get(self.episode.ruby).visual)
        self.life_potential.text = str(BuffSkillView._idols.get(self.episode.ruby).life)
        self.skill_potential.text = str(BuffSkillView._idols.get(self.episode.ruby).skill)

        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch: MotionEvent) -> Any:
        """
        Addselectionontouchdown

        :param MotionEvent touch:

        :return:
        :rtype: Any
        """

        if super().on_touch_down(touch):
            return True

        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv: RecycleView, index: int, is_selected: bool) -> None:
        """
        ビューの選択変更時、ビューに反映する。

        ``kivy.uix.recycleview.views.RecycleDataViewBehavior`` のオーバーライド専用メソッド。

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
        """
        各種絞り込み条件の変更に応じて、アイドルのエピソードを絞り込みを行う。

        - 所有、アイドルタイプ、レア度、特技発動間隔
        - センター効果分類説明
        - 特技分類
        """

        super().__init__(**kwargs)

        # 所有、アイドルタイプ、レア度、特技発動間隔で絞り込み
        self.framework.clear_widgets()

        self.hold = Factory.StrToggleButton(text="所有のみ", state="down")
        self.hold.bind(state=lambda instance, values: self.update())
        self.framework.add_widget(self.hold)

        self.framework.add_widget(Factory.StrView(text="タイプ"))
        self.cute = Factory.StrToggleButton(text="CUTE", state="down")
        self.cute.bind(state=lambda instance, values: self.update())
        self.framework.add_widget(self.cute)
        self.cool = Factory.StrToggleButton(text="COOL", state="down")
        self.cool.bind(state=lambda instance, values: self.update())
        self.framework.add_widget(self.cool)
        self.passion = Factory.StrToggleButton(text="PASSION", state="down")
        self.passion.bind(state=lambda instance, values: self.update())
        self.framework.add_widget(self.passion)

        self.framework.add_widget(Factory.StrView(text="レア度"))
        self.usrplus = Factory.StrToggleButton(text="USRPLUS", state="normal")
        self.usrplus.bind(state=lambda instance, values: self.update())
        self.framework.add_widget(self.usrplus)
        self.ssrplus = Factory.StrToggleButton(text="SSRPLUS", state="down")
        self.ssrplus.bind(state=lambda instance, values: self.update())
        self.framework.add_widget(self.ssrplus)
        self.srplus = Factory.StrToggleButton(text="SRPLUS", state="normal")
        self.srplus.bind(state=lambda instance, values: self.update())
        self.framework.add_widget(self.srplus)
        self.rplus = Factory.StrToggleButton(text="RPLUS", state="normal")
        self.rplus.bind(state=lambda instance, values: self.update())
        self.framework.add_widget(self.rplus)
        self.nplus = Factory.StrToggleButton(text="NPLUS", state="normal")
        self.nplus.bind(state=lambda instance, values: self.update())
        self.framework.add_widget(self.nplus)

        self.framework.add_widget(Factory.StrView(text="特技発動間隔"))
        for interval in sorted({skill.interval for skill in BuffSkillView._skills.gets()}, reverse=True):
            togglebutton = Factory.StrToggleButton(text=str(interval), state="down")
            togglebutton.bind(state=lambda instance, values: self.update())
            self.framework.add_widget(togglebutton)

        # センター効果分類説明で絞り込み
        self.buffselector.clear_widgets()
        for categoryname in sorted(BuffSkillView._buffs.categorynames):
            togglebutton = Factory.StrToggleButton(text=categoryname, state="normal")
            togglebutton.bind(state=lambda instance, values: self.update())
            self.buffselector.add_widget(togglebutton)

        # 特技分類で絞り込み
        self.skillselector.clear_widgets()
        for category in sorted(BuffSkillView._skills.categories):
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
            episodes_by_hold = {episode for episode in BuffSkillView._episodes.gets() if episode.star_rank > 0}
        else:
            episodes_by_hold = {episode for episode in BuffSkillView._episodes.gets()}

        # アイドルタイプでエピソードを制限
        episodes_by_type: set[Episode] = {
            episode
            for episode in BuffSkillView._episodes.gets()
            if episode.type.name in [type.text for type in [self.cute, self.cool, self.passion] if type.state == "down"]
        }

        # レア度でエピソードを制限
        episodes_by_rare: set[Episode] = {
            episode
            for episode in BuffSkillView._episodes.gets()
            if episode.rare.name
            in [
                rare.text
                for rare in [self.usrplus, self.ssrplus, self.srplus, self.rplus, self.nplus]
                if rare.state == "down"
            ]
        }

        # センター効果でエピソードを制限
        buffcategorynames: set[str] = {widget.text for widget in self.buffselector.children if widget.state == "down"}
        buffs: set[str] = set(
            itertools.chain.from_iterable(
                [BuffSkillView._buffs.buffs_by_categoryname(name) for name in buffcategorynames]
            )
        )
        episodes_by_buff: set[Episode] = {
            episode for episode in BuffSkillView._episodes.gets() if episode.buff_class in buffs
        }

        # 特技でエピソードを制限
        skillcategories: set[str] = {widget.text for widget in self.skillselector.children if widget.state == "down"}
        skills: set[str] = set(
            itertools.chain.from_iterable(
                [BuffSkillView._skills.skills_by_category(category) for category in skillcategories]
            )
        )
        episodes_by_skill: set[Episode] = {
            episode for episode in BuffSkillView._episodes.gets() if episode.skill_class in skills
        }

        # 特技発動間隔でエピソードを制限
        intervals: set[int] = {
            int(widget.text) for widget in self.framework.children if widget.text.isdigit() and widget.state == "down"
        }
        episodes_by_interval: set[Episode] = {
            episode
            for episode in BuffSkillView._episodes.gets()
            if BuffSkillView._skills.get(episode.skill).interval in intervals
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


class BuffSkillView(Factory.TabbedPanel):
    """
    立ち位置別、各種条件でアイドルのエピソードを絞り込むウィジット。

    :立ち位置:
      センター、左隣り、右隣り、左端、右端、ゲスト
    """

    centerposition = Factory.ObjectProperty(None)
    leftposition = Factory.ObjectProperty(None)
    rightposition = Factory.ObjectProperty(None)
    leftendposition = Factory.ObjectProperty(None)
    rightendposition = Factory.ObjectProperty(None)
    guestposition = Factory.ObjectProperty(None)

    _idols: Idols = Idols()
    _buffs: Buffs = Buffs()
    _skills: Skills = Skills()
    _episodes: Episodes = Episodes()

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        self.centerposition.add_widget(EpisodeSelector())
        self.leftposition.add_widget(EpisodeSelector())
        self.rightposition.add_widget(EpisodeSelector())
        self.leftendposition.add_widget(EpisodeSelector())
        self.rightendposition.add_widget(EpisodeSelector())
        self.guestposition.add_widget(EpisodeSelector())

        BuffSkillLogger.info(f"{self.__class__.__name__}: 初期化しました。")

    @classmethod
    def load(cls) -> None:
        """
        データベースの読み込み。
        """

        cls._idols.load()
        cls._episodes.load()
        cls._buffs.load()
        cls._skills.load()

        BuffSkillLogger.info(f"{cls.__name__}: データベースを読み込みました。")

    def close(self) -> None:
        """
        データベースの終了処理。
        """

        BuffSkillLogger.info(f"{self.__class__.__name__}: 終了します。")

    def update(self) -> None:
        """
        更新。
        """

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


if __name__ == "__main__":
    print(__file__)
