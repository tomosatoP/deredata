"""
メイン画面のモジュール。

:上部領域: データベース群
:中央領域: コマンド群。
:下部領域: シミュレーター。
"""

from random import choices
from string import ascii_letters, digits
from typing import Any
from itertools import product

from deredata.libs.database.units import Unit, Positions6
from deredata.libs.database.musics import Music

from deredata.unit import UnitView
from deredata.buffskill import BuffSkillView
from deredata.music import MusicView
from deredata.episode import EpisodeView
from deredata.idol import IdolView
from deredata.simulator import SimulatorView

from kivy.app import App
from kivy.factory import Factory
from kivy.uix.widget import Widget
from kivy.logger import Logger as MainviewLogger


COMMANDS: dict = {
    "楽曲一覧": {
        "楽曲一覧": "command_show_button",
    },
    "ユニット一覧": {
        "選択楽曲": "command_show_music_title",
        "ユニット名を編集": "command_edit_unit_name",
        "ユニット一覧に追加": "command_add_unit",
        "ユニット一覧から削除": "command_delete_unit",
        "シミュレーターに一括追加": "command_set_simulator_from_music_and_unit",
        "計算開始": "command_simulate",
    },
    "センター効果・特技": {
        "選択楽曲": "command_show_music_title",
        "シミュレーターに一括追加": "command_set_simulator_from_music_and_buffskill",
        "計算開始": "command_simulate",
    },
    "エピソード一覧": {
        "選択楽曲": "command_show_music_title",
        "センターに追加": "command_set_episode",
        "左隣りに追加": "command_set_episode",
        "右隣りに追加": "command_set_episode",
        "左端に追加": "command_set_episode",
        "右端に追加": "command_set_episode",
        "ゲストに追加": "command_set_episode",
        "計算開始": "command_simulate",
    },
    "アイドル一覧": {
        "アイドル一覧": "command_show_button",
    },
}


class DatabaseSeries(Factory.TabbedPanel):
    """
    DatabaseSeries
    """

    unitview = Factory.ObjectProperty(None)
    buffskillview = Factory.ObjectProperty(None)
    musicview = Factory.ObjectProperty(None)
    episodeview = Factory.ObjectProperty(None)
    idolview = Factory.ObjectProperty(None)

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        self.unitview.add_widget(UnitView())
        self.buffskillview.add_widget(BuffSkillView())
        self.musicview.add_widget(MusicView())
        self.episodeview.add_widget(EpisodeView())
        self.idolview.add_widget(IdolView())

    def update(self) -> None:

        self.unitview.content.update()
        self.buffskillview.content.update()
        self.episodeview.content.update()
        self.idolview.content.update()
        self.musicview.content.update()

    def close(self) -> None:

        self.unitview.content.close()
        self.buffskillview.content.close()
        self.episodeview.content.close()
        self.idolview.content.close()
        self.musicview.content.close()


class Deredata(Factory.BoxLayout):
    """
    メイン画面。
    """

    upperregion = Factory.ObjectProperty(None)
    commands = Factory.ObjectProperty(None)
    lowerregion = Factory.ObjectProperty(None)

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        # 上部領域にタブ（各種データベース）を追加。
        # カレントタブで中央のコマンド群を変更
        self.databaseseries = DatabaseSeries()
        self.databaseseries.bind(current_tab=lambda instance, item: self.set_commands(item.text))
        self.upperregion.add_widget(self.databaseseries)

        # 下部領域にシミュレーターを追加
        self.simulator = SimulatorView()
        self.lowerregion.add_widget(self.simulator)

    def close(self) -> None:
        """
        各種データベースの終了処理を行う。
        """

        self.databaseseries.close()

        MainviewLogger.info(f"{self.__class__.__name__}: 終了します。")

    def update(self) -> None:
        """
        各種データベースの更新処理を行う。
        """

        self.databaseseries.update()

    def set_commands(self, itemtitle: str) -> None:
        """
        表示されているデータベースに合わせてコマンド（ボタン）を変更する。
        """

        self.commands.clear_widgets()

        for key, value in COMMANDS[itemtitle].items():
            self.commands.add_widget(Factory.Button(text=key, on_release=getattr(self, value)))

    def command_show_button(self, instance: Widget) -> None: ...

    def command_show_music_title(self, instance: Widget) -> None:
        """
        選択されている楽曲を表示する。

        :param Widget instance: 呼び出したボタンウィジット。

        :todo: 表示する文字列を省略表記設定。
        """

        if self.databaseseries.musicview.content.selected():
            music: Music = self.databaseseries.musicview.content.selected()
            instance.text = "\n".join([music.song.category.name, music.song.name])
        else:
            instance.text = "選択楽曲"

    def command_set_episode(self, instance: Widget) -> None:
        """
        シミュレーターにライブを追加する。

        ライブは、**楽曲一覧** と **エピソード一覧** の組み合わせ
        """

        # 暫定：6人編成のみ処理
        if self.databaseseries.musicview.content.selected() and self.databaseseries.episodeview.content.selected():
            music: Music = self.databaseseries.musicview.content.selected()
            episodename: str = self.databaseseries.episodeview.content.selected().episode
            selected_live = self.simulator.selected()
            if selected_live:
                # 追加（選択状態）中のライブへのユニットを取得し、メンバーを追加。
                selected_music, selected_unit = selected_live
                match instance.text:
                    case "センターに追加":
                        selected_unit.positions.centerposition = episodename
                    case "左隣りに追加":
                        selected_unit.positions.leftposition = episodename
                    case "右隣りに追加":
                        selected_unit.positions.rightposition = episodename
                    case "左端に追加":
                        selected_unit.positions.leftendposition = episodename
                    case "右端に追加":
                        selected_unit.positions.rightendposition = episodename
                    case "ゲストに追加":
                        selected_unit.positions.guestposition = episodename
                    case _:
                        MainviewLogger.error(f"{self.__class__.__name__}.command_set_episode: メンバーの未指定。")

                self.simulator.simulatordataviews.refresh_from_data()

            else:
                # 追加（選択状態）中のライブが無いので、ライブを新規作成（楽曲、空ユニット）＆メンバー追加。
                # ライブは、追加（選択状態）中とする。
                unit: Unit = Unit(
                    name="".join(choices(ascii_letters + digits, k=10)),
                    positions=Positions6(),
                )
                match instance.text:
                    case "センターに追加":
                        unit.positions.centerposition = episodename
                    case "左隣りに追加":
                        unit.positions.leftposition = episodename
                    case "右隣りに追加":
                        unit.positions.rightposition = episodename
                    case "左端に追加":
                        unit.positions.leftendposition = episodename
                    case "右端に追加":
                        unit.positions.rightendposition = episodename
                    case "ゲストに追加":
                        unit.positions.guestposition = episodename
                    case _:
                        MainviewLogger.error(f"{self.__class__.__name__}.command_set_episode: メンバーの未指定。")

                self.simulator.unit_live(music=music, unit=unit)

    def command_edit_unit_name(self, instance: Widget) -> None: ...

    def command_add_unit(self, instance: Widget) -> None: ...

    def command_delete_unit(self, instance: Widget) -> None: ...

    def command_set_simulator_from_music_and_unit(self, instance: Widget) -> None:
        """
        シミュレーターにライブを一括登録する。

        ライブは、 **楽曲一覧** と **ユニット一覧** の組み合わせ。
        """

        if self.databaseseries.musicview.content.selected() and self.databaseseries.unitview.content.selected():
            for unit in self.databaseseries.unitview.content.selected():
                self.simulator.unit_live(music=self.databaseseries.musicview.content.selected(), unit=unit)

    def command_set_simulator_from_music_and_buffskill(self, instance: Widget) -> None:
        """
        シミュレーターにライブを一括登録する。

        ライブは、 **楽曲一覧** と **センター効果・特技** の組み合わせ。

        :todo: センター効果・特技の選択で場合分け
        :todo: 6人編成、5人編成、グランドライブ編成ABCの場合分け
        :todo: 組み合せが多いと、kivyサイクルをブロック
        """

        # 暫定：6人編成のみ処理
        if self.databaseseries.musicview.content.selected() and self.databaseseries.buffskillview.content.selected():
            for center, left, right, leftend, rightend, guest in product(
                *self.databaseseries.buffskillview.content.selected(),
            ):
                if len({center, left, right, leftend, rightend}) == 5:
                    # ゲストを除きユニット内でエピソードの重複は不可

                    self.simulator.unit_live(
                        music=self.databaseseries.musicview.content.selected(),
                        unit=Unit(
                            name="".join(choices(ascii_letters + digits, k=10)),
                            positions=Positions6(
                                centerposition=center.episode,
                                leftposition=left.episode,
                                rightposition=right.episode,
                                leftendposition=leftend.episode,
                                rightendposition=rightend.episode,
                                guestposition=guest.episode,
                            ),
                        ),
                    )

    def command_simulate(self, instance: Widget) -> None:
        """
        シミュレーションを実行する。
        """

        self.simulator.simulate_live()


class MainviewApp(App):
    """アプリ"""

    def build(self) -> Deredata:

        UnitView.load()
        IdolView.load()
        EpisodeView.load()
        BuffSkillView.load()
        MusicView.load()
        SimulatorView.load()

        self.root = Deredata()
        self.root.update()

        return self.root

    def on_stop(self) -> None:

        self.root.close()
        super().on_stop()


if __name__ == "__main__":
    print(__file__)
