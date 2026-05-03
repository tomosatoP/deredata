"""
モジュール。
"""

from typing import Any
from itertools import product

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
    "シミュレーターから\nユニット一覧にユニットを追加": "add_unit",
    "ユニット一覧から\nユニットを削除": "delete_unit",
    "楽曲一覧とユニット一覧から\nシミュレーターに追加": "set_simulator_from_music_and_unit",
    "楽曲一覧とセンター効果・特技から\nシミュレーターに一括追加": "set_simulator_from_music_and_buffskill",
    "シミュレーターから削除": "delete_set",
    "計算開始": "simulate",
}


class DatabaseSeries(Factory.TabbedPanel):
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
    upperregion = Factory.ObjectProperty(None)
    commands = Factory.ObjectProperty(None)
    lowerregion = Factory.ObjectProperty(None)

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        self.databaseseries = DatabaseSeries()
        self.upperregion.add_widget(self.databaseseries)

        for item in COMMANDS.keys():
            self.commands.add_widget(Factory.Button(text=item, on_release=lambda instance: self.command(instance)))

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

    def command(self, widget: Widget) -> None:
        getattr(self, COMMANDS.get(widget.text, "na"))()

    def add_unit(self) -> None:
        pass

    def delete_unit(self) -> None:
        pass

    def set_simulator_from_music_and_unit(self) -> None:
        if self.databaseseries.musicview.content.selected() and self.databaseseries.unitview.content.selected():
            for music, unit in product(
                self.databaseseries.musicview.content.selected(),
                self.databaseseries.unitview.content.selected(),
            ):
                self.simulator.unit_live(music=music, unit=unit)

    def set_simulator_from_music_and_buffskill(self) -> None:
        pass

    def delete_set(self) -> None:
        pass

    def simulate(self) -> None:
        self.simulator.simulate_live()


class MainviewApp(App):
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
