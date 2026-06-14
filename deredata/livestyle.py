"""
ライブスタイル選択のモジュール
"""

from typing import Any

from kivy.factory import Factory
from kivy.uix.widget import Widget
from kivy.logger import Logger as LiveStyleLogger


class SelectionLabel(Factory.Label):
    selected = Factory.BooleanProperty(None)
    selectable = Factory.BooleanProperty(True)


class SelectionLayout(Factory.BoxLayout):
    number = Factory.ObjectProperty(None)
    effect = Factory.ObjectProperty(None)
    effectlist = Factory.ObjectProperty(None)

    selected = Factory.BooleanProperty(None)
    selectable = Factory.BooleanProperty(True)

    def content(self, number: str, effect: str, effectlist: list[str]) -> None:
        self.number.text = number
        self.effect.text = effect
        self.effectlist.text = effectlist[0]
        self.effectlist.values = effectlist


class LiveStyleView(Factory.CompoundSelectionBehavior, Factory.BoxLayout):
    regularlive = Factory.ObjectProperty(None)
    grandlivea = Factory.ObjectProperty(None)
    grandliveb = Factory.ObjectProperty(None)
    grandlivec = Factory.ObjectProperty(None)
    year = Factory.ObjectProperty(None)
    season = Factory.ObjectProperty(None)
    rank = Factory.ObjectProperty(None)
    booth1 = Factory.ObjectProperty(None)
    booth2 = Factory.ObjectProperty(None)
    booth3 = Factory.ObjectProperty(None)
    booth4 = Factory.ObjectProperty(None)
    booth5 = Factory.ObjectProperty(None)
    booth6 = Factory.ObjectProperty(None)
    booth7 = Factory.ObjectProperty(None)
    booth8 = Factory.ObjectProperty(None)
    booth9 = Factory.ObjectProperty(None)
    booth10a = Factory.ObjectProperty(None)
    booth10b = Factory.ObjectProperty(None)
    booth10c = Factory.ObjectProperty(None)

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        for live in self.get_selectable_nodes():
            live.bind(on_touch_down=self.do_touch)

        self.livecarnival()
        self.select_node(self.regularlive)

        LiveStyleLogger.info(f"{self.__class__.__name__}: 初期化しました。")

    def close(self) -> None:

        LiveStyleLogger.info(f"{self.__class__.__name__}: 終了します。")

    def do_touch(self, instance: Widget, touch: Any) -> bool:
        if instance.collide_point(*touch.pos):
            if isinstance(instance, SelectionLayout) and instance.effectlist.collide_point(*touch.pos):
                return False
            self.select_with_touch(instance, touch)
        else:
            return False
        return True

    def get_selectable_nodes(self) -> list:

        return [
            self.regularlive,  # SelectionLabel
            self.grandlivea,
            self.grandliveb,
            self.grandlivec,
            self.booth1,  # SelectionLayout
            self.booth2,
            self.booth3,
            self.booth4,
            self.booth5,
            self.booth6,
            self.booth7,
            self.booth8,
            self.booth9,
            self.booth10a,
            self.booth10b,
            self.booth10c,
        ]

    def livecarnival(self) -> None:
        self.booth1.content("BOOTH 1", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])
        self.booth2.content("BOOTH 2", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])
        self.booth3.content("BOOTH 3", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])
        self.booth4.content("BOOTH 4", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])
        self.booth5.content("BOOTH 5", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])
        self.booth6.content("BOOTH 6", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])
        self.booth7.content("BOOTH 7", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])
        self.booth8.content("BOOTH 8", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])
        self.booth9.content("BOOTH 9", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])
        self.booth10a.content("BOOTH 10 A", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])
        self.booth10b.content("BOOTH 10 B", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])
        self.booth10c.content("BOOTH 10 C", "ブース効果", ["ブース効果リスト1", "ブース効果リスト2"])

    def select_node(self, node: Widget) -> None:
        super().select_node(node)

        node.selected = True

    def deselect_node(self, node: Widget) -> None:
        super().deselect_node(node)

        node.selected = False

    def selected(self) -> list:
        result: Widget = [node for node in self.get_selectable_nodes() if node.selected][0]
        if isinstance(result, SelectionLabel):
            return [result.text]
        elif isinstance(result, SelectionLayout):
            return [result.number.text, result.effect.text, result.effectlist.text, result.effectlist.values]
        return list()


if __name__ == "__main__":
    print(__file__)
