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

        self.music: Music = Music()
        self.bind(size=lambda instance, value: self.update(self.music))

    def clear(self) -> None:
        """
        デレステ譜面の表示をクリアする。
        """

        self.canvas.clear()

    def update(self, music: Music = Music()) -> None:
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

        self.music = music

        self.canvas.clear()
        if self.music.note_number != 0:
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
        データの作成・変更時、ビューに反映する。

        :param RecycleView rv: ビューの親リサイクルビュー。
        :param int index: ビューのインデックス。
        :param dict data: ビューに表示するデータ。

        :return: 継承元クラスのメソッドを呼び出す。
        :rtype: Any
        """

        self.index = index

        self.songcategory.text = data["musicdata"].song.name
        self.songtype.text = data["musicdata"].song.type.name
        self.songtitle.text = data["musicdata"].song.name
        self.songlevel.text = str(data["musicdata"].song.level)
        self.songtime.text = str(data["musicdata"].length)
        self.notenumber.text = str(data["musicdata"].note_number)
        self.flicknumber.text = str(data["musicdata"].flick_number)
        self.longnumber.text = str(data["musicdata"].long_number)
        self.slidenumber.text = str(data["musicdata"].slide_number)

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

        music: Music = self.musicdataviews.data[selected_nodes[0]]["musicdata"] if selected_nodes else Music()
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

    def selected(self) -> Music | None:
        """
        選択されているデレステ譜面データを返す。選択されていない場合は ``None`` を返す。
        """

        index: int = (
            self.musicdataviews.layout_manager.selected_nodes[0]
            if self.musicdataviews.layout_manager.selected_nodes
            else -1
        )

        return self.musicdataviews.data[index]["musicdata"] if index >= 0 else None


if __name__ == "__main__":
    print(__file__)
