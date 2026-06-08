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
        データの作成・変更時、ビューに反映する。

        :param RecycleView rv: ビューの親リサイクルビュー。
        :param int index: ビューのインデックス。
        :param dict data: ビューに表示するデータ。

        :return: 継承元クラスのメソッドを呼び出す。
        :rtype: Any
        """

        self.index = index

        self.name.text = data["unitdata"].name
        self.centerposition.text = data["unitdata"].positions.centerposition
        self.leftposition.text = data["unitdata"].positions.leftposition
        self.rightposition.text = data["unitdata"].positions.rightposition
        self.leftendposition.text = data["unitdata"].positions.leftendposition
        self.rightendposition.text = data["unitdata"].positions.rightendposition
        self.guestposition.text = data["unitdata"].positions.guestposition

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


class UnitView(Factory.BoxLayout):
    """
    ユニットデータベースを表示するウィジェット。
    """

    unitdataviews = Factory.ObjectProperty(None)

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)
        self._units: Units = Units()

        UnitLogger.info(f"{self.__class__.__name__}: 初期化しました。")

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
        self.unitdataviews.data = [{"unitdata": unit} for unit in sorted(self._units.gets())]

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
