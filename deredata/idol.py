"""
アイドルのデータとプロフィールを表示するモジュール。

:todo: アイドルのデータ（ポテンシャル）変更をデータベースに反映する処理を追加する。
"""

from typing import Any

from deredata.libs.database.idols import Idol, Idols
from deredata.libs.database.profiles import Profile, Profiles

from kivy.factory import Factory
from kivy.input.motionevent import MotionEvent
from kivy.uix.recycleview import RecycleView
from kivy.logger import Logger as IdolLogger

HIRAGANA: dict[str, tuple[str, ...]] = {
    "あ行": ("あ", "い", "う", "え", "お"),
    "か行": ("か", "き", "く", "け", "こ"),
    "さ行": ("さ", "し", "す", "せ", "そ"),
    "た行": ("た", "ち", "つ", "て", "と"),
    "な行": ("な", "に", "ぬ", "ね", "の"),
    "は行": ("は", "ひ", "ふ", "へ", "ほ"),
    "ま行": ("ま", "み", "む", "め", "も"),
    "や行": ("や", "ゆ", "よ"),
    "ら行": ("ら", "り", "る", "れ", "ろ"),
    "わ行": ("わ",),
}


class IdolDataViewclass(Factory.RecycleDataViewBehavior, Factory.BoxLayout):
    """
    アイドルのデータを表示するウィジット。

    ``RecycleView`` のビュー **viewclass**。
    ``RecycleView`` のレイアウト ``LayoutSelectionBehavior`` により、選択操作が可能。
    """

    index = None
    selected = Factory.BooleanProperty(False)
    selectable = Factory.BooleanProperty(True)

    def on_potential_changed(self) -> None:
        """
        ポテンシャル（ボーカル、ダンス、ビジュアル、ライフ、スキル）数値入力時、表示を更新する。

        :todo: アイドルデータのデータベースに反映。
        """

        sum: int = 0
        for widget in [self.vocal, self.dance, self.visual, self.life, self.skill]:
            widget.text = str(min(max(int(widget.text), 0), 10))
            sum += int(widget.text)

        self.sum.text = str(sum)

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

        self.idol = data["idoldata"]
        self.index = index

        self.name.text = self.idol.name
        self.type.text = self.idol.type.name
        self.sum.text = str(sum([self.idol.vocal, self.idol.dance, self.idol.visual, self.idol.life, self.idol.skill]))
        self.vocal.text = str(self.idol.vocal)
        self.dance.text = str(self.idol.dance)
        self.visual.text = str(self.idol.visual)
        self.life.text = str(self.idol.life)
        self.skill.text = str(self.idol.skill)
        self.overflow.text = "0"

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
        self.vocal.readonly = not is_selected
        self.dance.readonly = not is_selected
        self.visual.readonly = not is_selected
        self.life.readonly = not is_selected
        self.skill.readonly = not is_selected


class IdolProfileElementView(Factory.BoxLayout):
    """
    アイドルのプロフィールの要素を表示するためのウィジット。
    """

    title = Factory.ObjectProperty(None)
    value = Factory.ObjectProperty(None)

    def update(self, title: str, value: str) -> None:
        """
        アイドルのプロフィール要素の内容を更新する。

        :param str title: 項目名。
        :param str value: 内容。
        """

        self.title.text = title
        self.value.text = value


class IdolProfileView(Factory.BoxLayout):
    """
    アイドルのプロフィールを表示するためのウィジット。
    """

    def update(self, profile: Profile = Profile()) -> None:
        """
        アイドルのプロフィールを更新する。

        :param Profile profile: アイドルのプロフィール。
        """

        self.ruby.update("ふりがな", profile.ruby)
        self.age.update("年齢", profile.age)
        self.birthday.update("誕生日", profile.birthday)
        self.zodiac_sign.update("星座", profile.zodiac_sign)
        self.blood_type.update("血液型", profile.blood_type)
        self.profileheight.update("身長", profile.height)
        self.weight.update("体重", profile.weight)
        self.bust.update("バスト", profile.bust)
        self.waist.update("ウエスト", profile.waist)
        self.hip.update("ヒップ", profile.hip)
        self.dominant_hand.update("利き手", profile.dominant_hand)
        self.home.update("出身県", profile.home)
        self.hobbies.update("趣味", profile.hobbies)
        self.cv.update("声優", profile.cv)
        self.registration_date.update("登録日", profile.registration_date)


class IdolView(Factory.BoxLayout):
    """
    アイドルのデータとプロフィールを表示するためのウィジット。
    """

    idoldatalabel = Factory.ObjectProperty(None)
    idoldataviews = Factory.ObjectProperty(None)
    idolprofileview = Factory.ObjectProperty(None)

    _idols: Idols = Idols()
    _profiles: Profiles = Profiles()

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)

        self.idoldatalabel.name.values = list(HIRAGANA)
        self.idoldatalabel.type.values = ["CUTE", "COOL", "PASSION"]

        self.idoldatalabel.name.text = "あ行"
        self.idoldatalabel.type.text = "CUTE"

        self.idoldatalabel.name.bind(text=lambda name, value: self.update())
        self.idoldatalabel.type.bind(text=lambda type, value: self.update())
        self.idoldataviews.layout_manager.bind(selected_nodes=lambda instacne, values: self.update_profile(values))

        IdolLogger.info(f"{self.__class__.__name__}: 初期化しました。")

    @classmethod
    def load(cls) -> None:
        """
        アイドルのデータとプロフィールのデータベースを読み込む。
        """

        cls._idols.load()
        cls._profiles.load()

        IdolLogger.info(f"{cls.__name__}: データベースを読み込みました。")

    def close(self) -> None:
        """
        アイドルのデータとプロフィールのデータベースを閉じる。

        :todo: アイドルデータ（ポテンシャル）の変更点をデータベースに反映する処理を追加する。
        """

        IdolLogger.info(f"{self.__class__.__name__}: 終了します。")

    def update_profile(self, selected_nodes: list[int] = []) -> None:
        """
        選択によってアイドルプロフィールの表示を更新する。
        """

        profile: Profile = (
            IdolView._profiles.get(self.idoldataviews.data[selected_nodes[0]]["idoldata"].ruby)
            if selected_nodes
            else Profile()
        )
        self.idolprofileview.update(profile)

    def update(self) -> None:
        """
        アイドルのデータの表示を更新する。

        アイドルの **ふりがな** と **タイプ** の選択に基づいて、表示するアイドルのデータを更新する。
        """

        # ふりがなでアイドルを絞り込む。
        idols = filter(
            lambda idol: (
                idol.ruby.startswith(HIRAGANA.get(self.idoldatalabel.name.text, ()))
                and idol.type.name == self.idoldatalabel.type.text
            ),
            sorted(IdolView._idols.gets(), key=lambda x: x.ruby),
        )

        self.idoldataviews.layout_manager.clear_selection()
        self.idoldataviews.data = [{"idoldata": idol} for idol in idols]
        self.update_profile()

    def selected(self) -> list[Idol]:
        """
        選択されているアイドルデータを返す。
        """

        result: list[Idol] = [
            data["idoldata"]
            for i, data in enumerate(self.idoldataviews.data)
            if i in self.idoldataviews.layout_manager.selected_nodes
        ]
        return result


if __name__ == "__main__":
    print(__file__)
