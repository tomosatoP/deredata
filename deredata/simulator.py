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
from kivy.input.motionevent import MotionEvent
from kivy.uix.recycleview import RecycleView
from kivy.logger import Logger as SimulatorLogger


class SimulatorDataViewclass(Factory.RecycleDataViewBehavior, Factory.BoxLayout):
    """
    シミュレーターデータを表示するウィジェット。
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
        :param dict data: ビューに結びつけられたデータ。

        :return: 継承元クラスのメソッドを呼び出す。
        :rtype: Any
        """

        self.index = index

        self.music: Music = data["music"]
        self.unit: Unit = data["unit"]
        self.scoreview.text = "/".join([str(data["median"]), str(data["max"])])

        if data["status"] == "追加":
            # ビューに追加した時に、アピール値計算を行っておく。
            self.appeals: Calculator = Calculator(self.music)
            self.appeals.run(self.unit)
            data["status"] = "アピール値計算完了"
        self.progressview.text = data["status"]

        self.musicname.text = self.music.song.name
        self.centerepisode.text = self.unit.positions.centerposition
        self.leftepisode.text = self.unit.positions.leftposition
        self.rightepisode.text = self.unit.positions.rightposition
        self.leftendepisode.text = self.unit.positions.leftendposition
        self.rightendepisode.text = self.unit.positions.rightendposition
        self.guestepisode.text = self.unit.positions.guestposition

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
        """
        シミュレーターにライブを追加する。

        :param Music music: ライブのデレステ譜面データ。
        :param Unit unit: ライブのユニット。

        :todo: 追加したら選択状態にしたい。
        """

        self.simulatordataviews.data.append({"music": music, "unit": unit, "status": "追加", "median": 0, "max": 0})

    def buffskill_live(self) -> None:
        pass

    def clear_live(self) -> None:
        pass

    def simulate_live(self) -> None:
        """
        ライブをシミュレーションする。

        シミュレーションを非同期タスクに投入し、完了したらデータ更新を行う（ビューの更新に波及する）。
        """

        for live in self.simulatordataviews.layout_manager.children:
            task = create_task(self.async_process_pool_simulate(live))
            task.add_done_callback(self.simulatordataviews.refresh_from_data)

    async def async_process_pool_simulate(self, live: Widget) -> None:
        """
        デレステライブのスコア計算の進捗を live ウィジットに表示する。

        非同期および複数プロセスで実行されたデレステライブのスコア計算結果を順次に受け取り、
        進捗度（計算回数）を live ウィジットに表示する。
        全ての計算が完了したら、統計処理（中央値／最大値）の結果を data に反映する。

        :param Widget live: スコア計算の条件（デレステ楽曲、ユニットメンバーなど）を保持しているウィジット。
        """

        i: int = 0
        items: list = []
        async for item in self.processpool_simulate(live):
            i += 1
            live.progressview.text = str(i)
            items.append(sum(item))

        live.selected = False
        self.simulatordataviews.data[live.index]["status"] = "完了"
        self.simulatordataviews.data[live.index]["max"] = int(max(items))
        self.simulatordataviews.data[live.index]["median"] = int(median(items))

    async def processpool_simulate(self, live: Widget) -> AsyncGenerator:
        """
        デレステライブのスコア計算を実行する。

        特技発動確率で計算結果が変動するので、複数回計算を行う。
        計算の実行時間が長いので、複数プロセスに分散する。
        完了するまで kivy クロックをブロックさせないため、非同期にそれぞれの計算結果を取り出す。

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
