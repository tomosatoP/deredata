"""
モジュール。
"""

from asyncio import as_completed, create_task, get_running_loop
from typing import Any
from statistics import median
from collections.abc import AsyncGenerator
from concurrent.futures import ProcessPoolExecutor

from deredata.libs.database.idols import Idols
from deredata.libs.database.episodes import Episode, Episodes
from deredata.libs.database.buffs import Buffs
from deredata.libs.database.skills import Skills
from deredata.libs.database.units import Unit
from deredata.libs.database.musics import Music

from deredata.libs.simulate.appeal import Calculator
from deredata.libs.simulate.stage import Simulator


from kivy.uix.widget import Widget
from kivy.factory import Factory
from kivy.logger import Logger as SimulatorLogger


class SimulatorDataView(Factory.BoxLayout):
    musicname = Factory.ObjectProperty(None)
    centerepisode = Factory.ObjectProperty(None)
    leftepisode = Factory.ObjectProperty(None)
    rightepisode = Factory.ObjectProperty(None)
    leftendepisode = Factory.ObjectProperty(None)
    rightendepisode = Factory.ObjectProperty(None)
    guestepisode = Factory.ObjectProperty(None)
    progressview = Factory.ObjectProperty(None)
    scoreview = Factory.ObjectProperty(None)

    def __init__(self, music: Music, unit: Unit, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        self.music: Music = music
        self.unit: Unit = unit

        self.appeals = Calculator(self.music)
        self.appeals.run(self.unit)

        self.musicname.text = "Lv" + str(self.music.song.level) + ", " + self.music.song.name
        self.centerepisode.text = self.unit.positions.centerposition
        self.leftepisode.text = self.unit.positions.leftposition
        self.rightepisode.text = self.unit.positions.rightposition
        self.leftendepisode.text = self.unit.positions.leftendposition
        self.rightendepisode.text = self.unit.positions.rightendposition
        self.guestepisode.text = self.unit.positions.guestposition

        self.progressview.text = "アピール値、取得済"
        self.scoreview.text = "未実施"


class SimulatorView(Factory.BoxLayout):
    simulatordataviews = Factory.ObjectProperty(None)

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        pass

    @classmethod
    def load(cls) -> None:
        Calculator.load()
        Simulator.load()

    def unit_live(self, music: Music, unit: Unit) -> None:
        self.simulatordataviews.add_widget(SimulatorDataView(music, unit))

    def buffskill_live(self) -> None:
        pass

    def clear_live(self) -> None:
        pass

    def simulate_live(self) -> None:

        for live in self.simulatordataviews.children:
            task = create_task(self.aaaaaa(live))
            while task.done():
                pass

    async def aaaaaa(self, live: Widget) -> None:
        """
        デレステライブのスコア計算の進捗を live ウィジットに表示する。

        非同期および複数プロセスで実行されたデレステライブのスコア計算結果を順次に受け取り、
        進捗度（計算回数）を live ウィジットに表示する。
        全ての計算が完了したら、統計処理（中央値／最大値）の結果を live ウィジットに表示する。

        :param Widget live: スコア計算の条件（デレステ楽曲、ユニットメンバーなど）を保持しているウィジット。
        """

        i: int = 0
        items: list = []
        async for item in self.async_repeat_simulation(live):
            i += 1
            live.progressview.text = str(i)
            items.append(sum(item))

        self.max = int(max(items))
        self.median = int(median(items))

        live.scoreview.text = str(self.median) + " / " + str(self.max)

    async def async_repeat_simulation(self, live: Widget) -> AsyncGenerator:
        """
        デレステライブのスコア計算を実行する。

        特技発動確率で計算結果が変動するので、複数回計算を行う。
        計算の実行時間が長いので、複数プロセスに分散する。
        完了するまでアプリケーションが止まって見えるのを避けるために非同期にそれぞれの計算結果を取り出す。

        :param Widget live: スコア計算の条件（デレステ楽曲、ユニットメンバーなど）を保持しているウィジット。

        :return: 非同期に取り出されたそれぞれのスコアの計算結果で、ノートスコアのリスト。
        :rtype: AsyncGenerator
        """

        repetitions: int = 10
        workers: int = 4

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                get_running_loop().run_in_executor(
                    executor,
                    Simulator(live.music).run,
                    live.appeals.isresonance,
                    live.appeals.unit,
                    live.appeals.supports,
                )
                for _ in range(repetitions)
            ]

            for future in as_completed(futures):
                yield await future


if __name__ == "__main__":
    print(__file__)
