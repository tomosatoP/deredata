"""
アイドルのエピソードとエピソードフレーバを表示するモジュール。

:todo: スターランクの変更をデータベースに反映する処理を追加。
"""

from typing import Any
from math import ceil

from deredata.libs.database.enumerations import GachaType
from deredata.libs.database.idols import Idol, Idols
from deredata.libs.database.episodes import Episode, Episodes
from deredata.libs.database.flavors import Flavor, Flavors
from deredata.libs.database.buffs import Buffs
from deredata.libs.database.skills import probability_value, Skill, Skills
from deredata.libs.database.potentials import Potentials

from kivy.factory import Factory
from kivy.input.motionevent import MotionEvent
from kivy.uix.recycleview import RecycleView
from kivy.uix.widget import Widget
from kivy.logger import Logger as EpisodeLogger

HIRAGANA: dict[str, tuple[str, ...]] = {
    "あ行": ("あ", "い", "う", "え", "お"),
    "か行": ("か", "き", "く", "け", "こ", "が", "ぎ", "ぐ", "げ", "ご"),
    "さ行": ("さ", "し", "す", "せ", "そ", "ざ", "じ", "ず", "ぜ", "ぞ"),
    "た行": ("た", "ち", "つ", "て", "と", "だ", "ぢ", "づ", "で", "ど"),
    "な行": ("な", "に", "ぬ", "ね", "の"),
    "は行": ("は", "ひ", "ふ", "へ", "ほ", "ば", "び", "ぶ", "べ", "ぼ", "ぱ", "ぴ", "ぷ", "ぺ", "ぽ"),
    "ま行": ("ま", "み", "む", "め", "も"),
    "や行": ("や", "ゐ", "ゆ", "ゑ", "よ"),
    "ら行": ("ら", "り", "る", "れ", "ろ"),
    "わ行": ("わ", "を", "ん"),
}


class EpisodeFlavorElementView(Factory.BoxLayout):
    """
    アイドルのエピソードフレーバーの要素を表示するためのウィジット。
    """

    title = Factory.ObjectProperty(Factory.Label)
    value = Factory.ObjectProperty(Factory.Label)

    def update(self, title: str, value: str) -> None:
        """
        アイドルのエピソードフレーバーの要素の内容を更新する。

        :param str title: 項目名。
        :param str value: 内容。
        """

        self.title.text = title
        self.value.text = value


class EpisodeFlavorView(Factory.BoxLayout):
    """
    アイドルのエピソードフレーバーを表示するためのウィジット。
    """

    ruby = Factory.ObjectProperty(None)
    voice = Factory.ObjectProperty(None)
    solo = Factory.ObjectProperty(None)
    gacha = Factory.ObjectProperty(None)
    registration_date = Factory.ObjectProperty(None)
    buff = Factory.ObjectProperty(None)
    skill = Factory.ObjectProperty(None)
    altervocal = Factory.ObjectProperty(None)
    alterdance = Factory.ObjectProperty(None)
    altervisual = Factory.ObjectProperty(None)
    alterlife = Factory.ObjectProperty(None)
    alterskill = Factory.ObjectProperty(None)

    def update(self, flavor: Flavor = Flavor()) -> None:
        """
        アイドルのエピソードフレーバーを更新する。

        ポテンシャル補正、ルーム効果、楽曲タイプ一致効果補正後のアピール値も表示する。

        :param Flavor flavor: アイドルのエピソードフレーバー。
        """

        episode: Episode = EpisodeView._episodes.get(flavor.episode)
        skill: Skill = EpisodeView._skills.get(episode.skill)
        idol: Idol = EpisodeView._idols.get(episode.ruby)

        self.ruby.update("ふりがな", str(episode.ruby))

        self.voice.update("ボイス", str(flavor.voice))
        self.solo.update("ソロ", str(flavor.solo))
        self.gacha.update("入手枠", GachaType(flavor.gacha).value)
        self.registration_date.update("登録日", flavor.registration_date)

        self.buff.update("センター効果", episode.buff_class)
        self.skill.update("特技", episode.skill_class)

        self.altervocal.update(
            "ボーカル",
            str(ceil((episode.vocal + EpisodeView._potentials.value("ボーカル", episode.rare, idol.vocal)) * 1.4))
            + f"({idol.vocal})",
        )
        self.alterdance.update(
            "ダンス",
            str(ceil((episode.dance + EpisodeView._potentials.value("ダンス", episode.rare, idol.dance)) * 1.4))
            + f"({idol.dance})",
        )
        self.altervisual.update(
            "ビジュアル",
            str(ceil((episode.visual + EpisodeView._potentials.value("ビジュアル", episode.rare, idol.visual)) * 1.4))
            + f"({idol.visual})",
        )
        self.alterlife.update(
            "ライフ",
            str(episode.life + EpisodeView._potentials.value("ライフ", episode.rare, idol.life)) + f"({idol.life})",
        )
        self.alterskill.update(
            "特技発動確率(%)",
            str(
                ceil(
                    (
                        probability_value(skill.probability) * (1.00 + (episode.skill_level - 1.0) / 18.0)
                        + EpisodeView._potentials.value("特技発動率", episode.rare, idol.skill)
                    )
                    * 130
                )
            )
            + f"({idol.skill})",
        )


class EpisodeDataViewclass(Factory.RecycleDataViewBehavior, Factory.BoxLayout):
    """
    アイドルのエピソードの各種データを表示するウィジット。
    """

    index = None
    selected = Factory.BooleanProperty(False)
    selectable = Factory.BooleanProperty(True)

    def on_potential_changed(self, widget: Widget) -> None:
        """
        スターランクの数値入力時、表示を更新する。

        :todo: エピソードデータのデータベースに反映。
        """

        if widget == self.star_rank:
            match self.rare.text:
                case "USRPLUS" | "USR":
                    widget.text = str(min(max(int(widget.text), 0), 20))

                case "SSRPLUS" | "SSR":
                    widget.text = str(min(max(int(widget.text), 0), 20))

                case "SRPLUS" | "SR":
                    widget.text = str(min(max(int(widget.text), 0), 15))

                case "RPLUS" | "R":
                    widget.text = str(min(max(int(widget.text), 0), 10))

                case "NPLUS" | "N":
                    widget.text = str(min(max(int(widget.text), 0), 5))

                case _:
                    EpisodeLogger.error(f"{self.__class__.__name__}.on_potential_changed: レア度が範囲外です。")
        else:
            EpisodeLogger.error(f"{self.__class__.__name__}.on_potential_changed: スターランク以外が指定されました。")

    def refresh_view_attrs(self, rv: RecycleView, index: int, data: dict) -> Any:
        """
        データの変更、ビューポートの変更がビューに波及する際に、呼び出される。

        :param RecycleView rv: ビューの親リサイクルビュー。
        :param int index: ビューのインデックス。
        :param dict data: ビューに表示するデータ。

        :return: 継承元クラスのメソッドを呼び出す。
        :rtype: Any
        """

        self.index = index

        self.name.text = data["episodedata"].episode
        self.type.text = data["episodedata"].type.name
        self.dominant.text = data["episodedata"].dominant.name
        self.mystyle.text = str(data["episodedata"].mystyle)
        self.rare.text = data["episodedata"].rare.name
        self.buff_class.text = data["episodedata"].buff_class
        self.skill_class.text = data["episodedata"].skill_class
        self.star_rank.text = str(data["episodedata"].star_rank)
        self.skill_level.text = str(data["episodedata"].skill_level)
        self.level.text = str(data["episodedata"].level)
        self.affection.text = str(data["episodedata"].affection)
        self.vocal.text = str(data["episodedata"].vocal)
        self.dance.text = str(data["episodedata"].dance)
        self.visual.text = str(data["episodedata"].visual)
        self.life.text = str(data["episodedata"].life)

        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch: MotionEvent) -> Any:
        """
        タッチイベントを受け取ったとき、ビューの選択状態を変更する。

        ビューの継承元でタッチイベントを処理する場合を除き、タッチイベントを受け取とるとレイアウトにディスパッチする。

        :param MotionEvent touch: 受け取ったタッチイベント。

        :return:
            ``True`` の場合は、ビューの継承元クラスのインスタンスでタッチイベントを処理した。
            そうでない場合は、レイアウトにディスパッチ（結果として、選択状態を変更）。
        :rtype: Any
        """

        if super().on_touch_down(touch):
            return True

        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv: RecycleView, index: int, is_selected: bool) -> None:
        """
        ビューの選択変更時、ビューに反映する。

        ビューの選択変更時、ビューに反映する。また、選択状態でのみ、数値入力を可能にする。

        :param RecycleView rv: ビューの親リサイクルビュー。
        :param int index: ビューのインデックス。
        :param bool is_selected: ``True`` の場合は、ビューは選択された。``False`` の場合は、選択されなかった。
        """

        self.selected = is_selected
        self.star_rank.readonly = not is_selected


class EpisodeView(Factory.BoxLayout):
    """
    アイドルのエピソードとエピソードフレーバーを表示するためのウィジット。
    """

    episodedatalabel = Factory.ObjectProperty(None)
    episodedataviews = Factory.ObjectProperty(None)
    episodeflavorview = Factory.ObjectProperty(None)

    _idols: Idols = Idols()
    _episodes: Episodes = Episodes()
    _flavors: Flavors = Flavors()
    _buffs: Buffs = Buffs()
    _skills: Skills = Skills()
    _potentials: Potentials = Potentials()

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        self.episodedatalabel.name.values = list(HIRAGANA)
        self.episodedatalabel.type.values = ["CUTE", "COOL", "PASSION"]
        self.episodedatalabel.dominant.values = ["ドミナントを含むアイドル", "ドミナント"]
        self.episodedatalabel.mystyle.values = ["マイスタイルを含むアイドル", "マイスタイル"]
        self.episodedatalabel.rare.values = ["USRPLUS", "SSRPLUS", "SRPLUS", "RPLUS", "NPLUS"]
        self.episodedatalabel.buff_class.values = ["すべてのセンター効果"] + list(
            EpisodeView._buffs.buff_groupby_categorynames
        )
        self.episodedatalabel.skill_class.values = ["すべての特技"] + list(EpisodeView._skills.skill_groupby_categories)

        self.episodedatalabel.name.text = "あ行"
        self.episodedatalabel.type.text = "CUTE"
        self.episodedatalabel.dominant.text = "ドミナントを含むアイドル"
        self.episodedatalabel.mystyle.text = "マイスタイルを含むアイドル"
        self.episodedatalabel.rare.text = "SSRPLUS"
        self.episodedatalabel.buff_class.text = "すべてのセンター効果"
        self.episodedatalabel.skill_class.text = "すべての特技"

        self.episodedatalabel.name.bind(text=lambda name, value: self.update())
        self.episodedatalabel.type.bind(text=lambda name, value: self.update())
        self.episodedatalabel.dominant.bind(text=lambda name, value: self.update())
        self.episodedatalabel.mystyle.bind(text=lambda name, value: self.update())
        self.episodedatalabel.rare.bind(text=lambda name, value: self.update())
        self.episodedatalabel.buff_class.bind(text=lambda name, value: self.update())
        self.episodedatalabel.skill_class.bind(text=lambda name, value: self.update())

        self.episodedataviews.layout_manager.bind(selected_nodes=lambda instace, values: self.update_flavor(values))

        EpisodeLogger.info(f"{self.__class__.__name__}: 初期化しました。")

    @classmethod
    def load(cls) -> None:

        cls._idols.load()
        cls._episodes.load()
        cls._flavors.load()
        cls._buffs.load()
        cls._skills.load()
        cls._potentials.load()

        EpisodeLogger.info(f"{cls.__class__.__name__}: データベースを読み込みました。")

    def close(self) -> None:
        """
        データベースを閉じる。

        :todo: スターランクの変更をデータベースに反映する処理を追加。
        """

        EpisodeLogger.info(f"{self.__class__.__name__}: 終了します。")

    def update_flavor(self, selected_nodes: list[int] = []) -> None:

        flavor: Flavor = (
            EpisodeView._flavors.get(self.episodedataviews.data[selected_nodes[0]]["episodedata"].episode)
            if selected_nodes
            else Flavor()
        )
        self.episodeflavorview.update(flavor)

    def update(self) -> None:

        # アイドルのふりがな（頭文字のみ）の絞り込み
        episodes_by_ruby: set[Episode] = {
            episode
            for episode in EpisodeView._episodes.gets()
            if episode.ruby.startswith(HIRAGANA.get(self.episodedatalabel.name.text, ()))
        }

        # アイドルタイプの絞り込み
        episodes_by_type: set[Episode] = {
            episode for episode in EpisodeView._episodes.gets() if episode.type.name == self.episodedatalabel.type.text
        }

        # ドミナントアイドルタイプの絞り込み
        episodes_by_dominant: set[Episode] = (
            {
                episode
                for episode in EpisodeView._episodes.gets()
                if episode.dominant.name in ["CUTE", "COOL", "PASSION"]
            }
            if self.episodedatalabel.dominant.text != "ドミナントを含むアイドル"
            else EpisodeView._episodes.gets()
        )

        # マイスタイルの絞り込み
        episodes_by_mystyle: set[Episode] = (
            {episode for episode in EpisodeView._episodes.gets() if episode.mystyle}
            if self.episodedatalabel.mystyle.text != "マイスタイルを含むアイドル"
            else EpisodeView._episodes.gets()
        )

        # レア度の絞り込み
        episodes_by_rare: set[Episode] = {
            episode for episode in EpisodeView._episodes.gets() if episode.rare.name == self.episodedatalabel.rare.text
        }

        # センター効果の絞り込み
        episodes_by_buff: set[Episode] = (
            {
                episode
                for episode in EpisodeView._episodes.gets()
                if episode.buff_class
                in EpisodeView._buffs.buff_groupby_categorynames.get(self.episodedatalabel.buff_class.text, ())
            }
            if self.episodedatalabel.buff_class.text != "すべてのセンター効果"
            else EpisodeView._episodes.gets()
        )

        # 特技の絞り込み
        episodes_by_skill: set[Episode] = (
            {
                episode
                for episode in EpisodeView._episodes.gets()
                if episode.skill_class
                in EpisodeView._skills.skill_groupby_categories.get(self.episodedatalabel.skill_class.text, ())
            }
            if self.episodedatalabel.skill_class.text != "すべての特技"
            else EpisodeView._episodes.gets()
        )

        self.episodedataviews.layout_manager.clear_selection()
        self.episodedataviews.data = [
            {"episodedata": episode}
            for episode in sorted(
                episodes_by_ruby
                & episodes_by_type
                & episodes_by_dominant
                & episodes_by_mystyle
                & episodes_by_rare
                & episodes_by_buff
                & episodes_by_skill
            )
        ]

        self.episodeflavorview.update()

    def selected(self) -> Episode | None:
        """
        選択されているエピソードデータを返す。選択されていない場合は ``None`` を返す。
        """

        index: int = (
            self.episodedataviews.layout_manager.selected_nodes[0]
            if self.episodedataviews.layout_manager.selected_nodes
            else -1
        )

        return self.episodedataviews.data[index]["episodedata"] if index >= 0 else None


if __name__ == "__main__":
    print(__file__)
