"""
データベースからシミュレーションに適用するデレステ譜面データを選ぶモジュール。
"""

from typing import Any
from math import floor
from deredata.libs.database.musics import Note, NoteType, SongCategory, SongType, Music, Musics

from kivy.uix.widget import Widget
from kivy.factory import Factory
from kivy.input.motionevent import MotionEvent
from kivy.uix.recycleview import RecycleView
from kivy.graphics import Color, Line
from kivy.logger import Logger as MusicLogger


class TimeChart(Factory.Widget):
    """
    デレステ譜面を時系列に表示するウィジット。
    """

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        self.bind(size=lambda instance, value: self.update())

    def clear(self) -> None:
        """
        デレステ譜面の表示をクリアする。
        """

        self.canvas.clear()

    def update(self, music: Music | None = None) -> None:
        """
        デレステ譜面データを更新する。

        デレステ譜面データの選択が変更された時、またはウィジットのサイズが変更された時に呼び出される。

        :param Music music: デレステ譜面データ
        """

        def draw_noteline(widget: Widget, note: Note, length: int) -> None:
            """
            デレステ譜面のノートを時系列に表示する。
            """

            width = floor(widget.width / length)
            with widget.canvas:
                Color(1, 0, 0) if note.lane == 0 else Color(1, 1, 1)
                Line(
                    points=[
                        widget.x + note.timestamp * note.time_base * width,
                        widget.y + widget.height / 6 * (note.lane),
                        widget.x + note.timestamp * note.time_base * width,
                        widget.y + widget.height / 6 * ((note.lane + 1) if note.lane != 0 else 6),
                    ],
                    width=1,
                )

        def draw_counter(widget: Widget, note: Note, length: int) -> None:
            """
            デレステ譜面のカウンターを時系列に表示する。
            """
            width = floor(widget.width / length)
            if note.lane == 0:
                label = Factory.Label(
                    text=str(note.timestamp * note.time_base),
                    font_size=10,
                    size_hint=(None, None),
                    color=(1, 1, 0),
                    pos=(widget.x + note.timestamp * note.time_base * width, widget.y),
                )
                label.text_size = label.size
                label.halign = "left"
                widget.add_widget(label)

        self.music: Music | None = music if music is not None else self.music if hasattr(self, "music") else None

        self.canvas.clear()
        if self.music is not None:
            for note in self.music.notes(include_intervals=5):
                # 5秒ごとにカウンターを表示する。

                draw_noteline(self, note, self.music.length)
                draw_counter(self, note, self.music.length)


class MusicDataViewclass(Factory.RecycleDataViewBehavior, Factory.BoxLayout):
    """
    デレステ譜面データの各種情報を表示するウィジット。
    """

    index = None
    selected = Factory.BooleanProperty(False)
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

        self.music: Music = data["musicdata"]
        self.index = index

        self.songcategory.text = self.music.song.name
        self.songtype.text = self.music.song.type.name
        self.songtitle.text = self.music.song.name
        self.songlevel.text = str(self.music.song.level)
        self.songtime.text = str(self.music.length)
        self.notenumber.text = str(self.music.note_number)
        self.flicknumber.text = str(self.music.flick_number)
        self.longnumber.text = str(self.music.long_number)
        self.slidenumber.text = str(self.music.slide_number)

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


class MusicView(Factory.BoxLayout):
    """
    デレステ譜面データの選択と表示を管理するウィジット。
    """

    timechart = Factory.ObjectProperty(None)  # デレステ譜面データを時系列に表示するウィジット
    musicdatalabel = Factory.ObjectProperty(None)  # デレステ譜面データの項目ラベル
    musicdataviews = Factory.ObjectProperty(None)  # デレステ譜面データの選択対象リスト

    _musics: Musics = Musics()

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        self.musicdatalabel.songcategory.values = ["すべてのカテゴリー"] + [member.value for member in SongCategory]
        self.musicdatalabel.songtype.values = ["すべての楽曲タイプ"] + [member.value for member in SongType]
        self.musicdatalabel.songcategory.text = "すべてのカテゴリー"
        self.musicdatalabel.songtype.text = "すべての楽曲タイプ"

        self.musicdatalabel.songcategory.bind(text=lambda name, value: self.update())
        self.musicdatalabel.songtype.bind(text=lambda name, value: self.update())

        self.musicdataviews.layout_manager.bind(selected_nodes=lambda instance, values: self.update_timechart(values))

        MusicLogger.info(f"{self.__class__.__name__}: 初期化しました。")

    @classmethod
    def load(cls) -> None:
        """
        デレステ譜面ファイルデータベースを読み込む。
        """

        cls._musics.load()

        MusicLogger.info(f"{cls.__name__}: データベースを読み込みました。")

    def close(self) -> None:
        """
        デレステ譜面ファイルデータベースを閉じる。
        """

        MusicLogger.info(f"{self.__class__.__name__}: 終了します。")

    def update_timechart(self, selected_nodes: list[int] = []) -> None:

        music: Music | None = self.musicdataviews.data[selected_nodes[0]]["musicdata"] if selected_nodes else None
        self.timechart.update(music)

    def update(self) -> None:
        """
        デレステ譜面データの選択対象リストと表示を更新する。

        デレステ譜面データのカテゴリーまたは楽曲タイプの選択が変更されたときに呼び出される。
        """

        self.timechart.clear()

        # カテゴリーによるデレステ譜面データの選抜
        musics_by_category: set[Music] = (
            {
                music
                for music in MusicView._musics.gets()
                if music.song.category == self.musicdatalabel.songcategory.text
            }
            if self.musicdatalabel.songcategory.text != "すべてのカテゴリー"
            else MusicView._musics.gets()
        )

        # 楽曲タイプによるデレステ譜面データの選抜
        musics_by_type: set[Music] = (
            {music for music in MusicView._musics.gets() if music.song.type == self.musicdatalabel.songtype.text}
            if self.musicdatalabel.songtype.text != "すべての楽曲タイプ"
            else MusicView._musics.gets()
        )

        self.musicdataviews.layout_manager.clear_selection()
        self.musicdataviews.data = [
            {"musicdata": music}
            for music in sorted(
                musics_by_category & musics_by_type,
            )
        ]

    def selected(self) -> list[Music]:

        result: list[Music] = [
            data["musicdata"]
            for i, data in enumerate(self.musicdataviews.data)
            if i in self.musicdataviews.layout_manager.selected_nodes
        ]
        return result


if __name__ == "__main__":
    print(__file__)
