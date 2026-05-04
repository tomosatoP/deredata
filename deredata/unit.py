"""
データベースからシミュレーターに渡すユニットデータを扱うモジュール。

:todo: 追加機能、削除機能、編集機能、コピー機能とか
"""

from typing import Any
from deredata.libs.database.units import Unit, GrandliveUnit, Units

from kivy.factory import Factory
from kivy.input.motionevent import MotionEvent
from kivy.uix.recycleview import RecycleView
from kivy.logger import Logger as UnitLogger


class UnitDataViewclass(Factory.RecycleDataViewBehavior, Factory.BoxLayout):
    """
    ユニットデータベースのユニットデータを表示するウィジェット。
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

        self.unit = data["unitdata"]
        self.index = index

        self.name.text = self.unit.name
        self.centerposition.text = self.unit.positions.centerposition
        self.leftposition.text = self.unit.positions.leftposition
        self.rightposition.text = self.unit.positions.rightposition
        self.leftendposition.text = self.unit.positions.leftendposition
        self.rightendposition.text = self.unit.positions.rightendposition
        self.guestposition.text = self.unit.positions.guestposition

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


class UnitView(Factory.BoxLayout):
    """
    ユニットデータベースを表示するウィジェット。
    """

    unitdataviews = Factory.ObjectProperty(None)

    _units: Units = Units()

    @classmethod
    def load(cls) -> None:
        """
        ユニットデータベースを読み込む。
        """

        cls._units.load()

        UnitLogger.info(f"{cls.__name__}: データベースを読み込みました。")

    def close(self) -> None:
        """
        ユニットデータベースを閉じる。
        """

        UnitLogger.info(f"{self.__class__.__name__}: 終了します。")

    def update(self) -> None:
        """
        ユニットデータベースの内容を表示するウィジェットを更新する。
        """

        self.unitdataviews.layout_manager.clear_selection()
        self.unitdataviews.data = [{"unitdata": unit} for unit in sorted(UnitView._units.gets())]

    def selected(self) -> list[Unit | GrandliveUnit]:
        """
        ユニットデータベースの内容を表示するウィジェットから選択されたユニットデータを取得する。

        :return list[Unit | GrandliveUnit]: 選択されたユニットデータのリスト
        """

        result: list[Unit | GrandliveUnit] = [
            data["unitdata"]
            for i, data in enumerate(self.unitdataviews.data)
            if i in self.unitdataviews.layout_manager.selected_nodes
        ]

        return result


if __name__ == "__main__":
    print(__file__)
