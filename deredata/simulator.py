"""
シミュレーターのモジュール。
"""

from asyncio import as_completed, create_task, get_running_loop
from typing import Any
from statistics import median
from collections.abc import AsyncGenerator
from concurrent.futures import ProcessPoolExecutor

from deredata.libs.database.idols import Idol, Idols
from deredata.libs.database.episodes import Episode, Episodes
from deredata.libs.database.buffs import Buffs
from deredata.libs.database.skills import Skills
from deredata.libs.database.units import Unit
from deredata.libs.database.musics import Music

from deredata.libs.simulate.backstage import Calculator
from deredata.libs.simulate.stage import Simulator

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
        データの作成・変更時、ビューに反映する。

        :param RecycleView rv: ビューの親リサイクルビュー。
        :param int index: ビューのインデックス。
        :param dict data: ビューに表示するデータ。

        :return: 継承元クラスのメソッドを呼び出す。
        :rtype: Any
        """

        self.index = index

        self.musicname.text = data["music"].song.name

        self.centerepisode.text = data["unit"].positions.centerposition
        self.leftepisode.text = data["unit"].positions.leftposition
        self.rightepisode.text = data["unit"].positions.rightposition
        self.leftendepisode.text = data["unit"].positions.leftendposition
        self.rightendepisode.text = data["unit"].positions.rightendposition
        self.guestepisode.text = data["unit"].positions.guestposition

        self.progressview.text = data["status"]
        self.scoreview.text = "/".join([str(data["median"]), str(data["max"])])

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


class SimulatorView(Factory.BoxLayout):
    """
    シミュレーター（アピール値計算とスコア計算）。

    :ステータス 追加: ライブデータを追加し、アピール値計算待ち状態（楽曲と編成の確認）。
    :ステータス アピール値計算済: ライブデータのアピール値計算を完了し、スコア計算待ち状態。
    :ステータス （数字）: ライブデータの繰り返しスコア計算中。数字は終了したスコア計算の回数。
    :ステータス 完了: ライブデータの繰り返しスコア計算を終了した状態。
    """

    simulatordataviews = Factory.ObjectProperty(None)

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        self._episodes: Episodes = Episodes()

        SimulatorLogger.info(f"{self.__class__.__name__}: 初期化しました。")

    def close(self) -> None:

        SimulatorLogger.info(f"{self.__class__.__name__}: 終了します。")

    def unit_live(self, music: Music, unit: Unit) -> None:
        """
        シミュレーター（RecycleView）にライブデータを追加する。

        :param Music music: ライブのデレステ譜面データ。
        :param Unit unit: ライブのユニット。
        """

        # 6人編成のみ。
        # :todo: 6人編成を確認
        status: str = "追加"
        episodes: list[Episode] = [self._episodes.get(episodename) for episodename in unit.positions.list()]
        if music.note_number != 0 and len(episodes) == 6:
            appeal = Calculator(music)
            appeal.run(unit)
            status = "アピール値計算済"

        self.simulatordataviews.data.append(
            {
                "status": status,  # key_selection
                "music": music,
                "unit": unit,
                "appeal": appeal if status == "アピール値計算済" else 0,
                "median": 0,
                "max": 0,
            }
        )

    def buffskill_live(self) -> None: ...

    def simulate_live(self) -> None:
        """
        ライブデータ（状態：アピール値計算済）の繰り返しスコア計算を行う。

        繰り返しスコア計算を非同期タスクに投入し、完了したらデータ更新する（コールバック）。
        """

        for livedata in self.simulatordataviews.data:
            if livedata["status"] == "アピール値計算済":
                task = create_task(self._async_process_pool_simulate(livedata))
                task.add_done_callback(self.simulatordataviews.refresh_from_data)

    async def _async_process_pool_simulate(self, livedata: dict) -> None:
        """
        ライブデータの繰り返しスコア計算の進捗をステータスに書き込む。

        非同期および複数プロセスで実行されたライブデータの繰り返しスコア計算結果を順次に受け取り、
        進捗度（計算回数）をライブデータのステータスに書き込む。
        全ての計算が完了したら、統計処理（中央値／最大値）の結果をライブデータに反映する。

        :param dict livedata: スコア計算の条件（デレステ楽曲、ユニットメンバーなど）を保持しているライブデータ。
        """

        items: list = []
        async for i, result in self._processpool_simulate(livedata):
            livedata["status"] = str(i)
            items.append(sum(result))
            self.simulatordataviews.refresh_from_data()

        livedata["status"] = "完了"
        livedata["max"] = int(max(items))
        livedata["median"] = int(median(items))

        # :todo: シミュレーション完了後、ライブデータを選択状態を解除。
        # self.simulatordataviews.layout_manager.deselect_node(livedata["index"])

    async def _processpool_simulate(self, livedata: dict) -> AsyncGenerator:
        """
        ライブデータの非同期繰り返しスコア計算を実行する。

        特技発動確率で計算結果が変動するので、複数回計算を行う。
        計算の実行時間が長いので、複数プロセスに分散する。
        完了するまで kivy クロックをブロックさせないため、非同期にそれぞれの計算結果を取り出す。

        :param dict livedata: スコア計算の条件（デレステ楽曲、ユニットメンバーなど）を保持している。

        :return: 非同期に取り出されたそれぞれのスコアの計算結果で、ノートスコアのリスト。
        :rtype: AsyncGenerator
        """

        repetitions: int = 10
        workers: int = 4

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                get_running_loop().run_in_executor(
                    executor,
                    Simulator(livedata["music"]).run,
                    livedata["appeal"].isresonance,
                    livedata["appeal"].unit,
                    livedata["appeal"].supports,
                )
                for _ in range(repetitions)
            ]

            for i, future in enumerate(as_completed(futures), start=1):
                yield (i, await future)

    def selected(self) -> tuple[Music, Unit] | None:

        index: int = (
            self.simulatordataviews.layout_manager.selected_nodes[0]
            if self.simulatordataviews.layout_manager.selected_nodes
            else -1
        )
        return (
            (self.simulatordataviews.data[index]["music"], self.simulatordataviews.data[index]["unit"])
            if index >= 0
            else None
        )


if __name__ == "__main__":
    print(__file__)
