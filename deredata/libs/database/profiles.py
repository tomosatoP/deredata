"""
アイドル達のプロフィール情報を扱うモジュール。

:dataclass Profile: アイドルのプロフィール（名前、ポテンシャルなど）。
:class Profiles: アイドル達のプロフィールデータベース。
"""

import json
from pathlib import Path
from dataclasses import dataclass, field

from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsProfilesLogger

# アイドルのプロフィール情報データベースファイルパス
PROFILESDB: str = database_folder() + "profiles.json"


class ProfilesError(Exception):
    """
    profilesのエラーハンドラ
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsProfilesLogger.error(f"ProfilesError: {args}")


@dataclass(order=True, frozen=True)
class Profile:
    """
    アイドルのプロフィール（スコア計算に無関係）。

    :param str ruby: ふりがな
    :param str age: 年齢
    :param str birthday: 誕生日
    :param str zodiac_sign: 星座
    :param str blood_type: 血液型
    :param str height: 身長
    :param str weight: 体重
    :param str bust: バスト
    :param str waist: ウエスト
    :param str hip: ヒップ
    :param str dominant_hand: 利き手
    :param str home: 出身地
    :param str hobbies: 趣味
    :param str cv: 声優
    :param str registration_date: 登録日
    """

    ruby: str = "ふりがな"
    age: str = field(default="年齢", compare=False)
    birthday: str = field(default="誕生日", compare=False)
    zodiac_sign: str = field(default="星座", compare=False)
    blood_type: str = field(default="血液型", compare=False)
    height: str = field(default="身長", compare=False)
    weight: str = field(default="体重", compare=False)
    bust: str = field(default="バスト", compare=False)
    waist: str = field(default="ウエスト", compare=False)
    hip: str = field(default="ヒップ", compare=False)
    dominant_hand: str = field(default="利き手", compare=False)
    home: str = field(default="出身地", compare=False)
    hobbies: str = field(default="趣味", compare=False)
    cv: str = field(default="声優", compare=False)
    registration_date: str = field(default="登録日", compare=False)


class Profiles:
    """
    アイドル達のプロフィール情報データベース。
    """

    _profiles: set[Profile] = set()

    def get(self, ruby: str) -> Profile:
        result: set[Profile] = {profile for profile in self.__class__._profiles if profile.ruby == ruby}
        return result.pop() if result else Profile()

    def gets(self) -> set[Profile]:
        return self.__class__._profiles

    def add(self, profile: Profile) -> None:
        self.__class__._profiles.add(profile)

    def remove(self, profile: Profile) -> None:
        self.__class__._profiles.remove(profile)

    @classmethod
    def load(cls, filename: str = PROFILESDB) -> None:
        """
        アイドルのプロフィール情報データベースを保存する。

        :param str filename: 初期値は、既定のファイル名。

        :raise ProfilesError: アイドルプロフィール情報データベースを読み込めなかった。
        """

        path = Path(filename)
        if not isinstance(path, Path) or not path.exists() or not path.is_file():
            raise ProfilesError(f"{cls.__name__}.load: プロフィール情報データベースを読み込めませんでした。")

        with path.open("r", encoding="utf-8-sig") as f:
            datas = json.load(f)

        for data in datas:
            profile = Profile(
                ruby=data["ふりがな"],
                age=data["年齢"],
                birthday=data["誕生日"],
                zodiac_sign=data["星座"],
                blood_type=data["血液型"],
                height=data["身長"],
                weight=data["体重"],
                bust=data["バスト"],
                waist=data["ウエスト"],
                hip=data["ヒップ"],
                dominant_hand=data["利き手"],
                home=data["出身地"],
                hobbies=data["趣味"],
                cv=data["声優"],
                registration_date=data["登録日"],
            )
            cls._profiles.add(profile)

        LibsProfilesLogger.info(
            f"{cls.__name__}.load: {len(cls._profiles)}件のアイドルプロフィール情報データベースを読み込みました。"
        )

    @classmethod
    def save(cls, filename: str = PROFILESDB) -> None:
        """
        アイドルのプロフィール情報データベースを保存する。

        :param str filename: 初期値は、既定のファイル名。

        :raise ProfilesError: アイドルプロフィール情報データベースを保存できなかった。
        """

        path: Path = Path(filename)
        if not isinstance(path, Path):
            raise ProfilesError(f"{cls.__name__}.save: アイドルプロフィール情報を保存できませんでした。")

        profiles = [
            {
                "ふりがな": profile.ruby,
                "年齢": profile.age,
                "誕生日": profile.birthday,
                "星座": profile.zodiac_sign,
                "血液型": profile.blood_type,
                "身長": profile.height,
                "体重": profile.weight,
                "バスト": profile.bust,
                "ウエスト": profile.waist,
                "ヒップ": profile.hip,
                "利き手": profile.dominant_hand,
                "出身地": profile.home,
                "趣味": profile.hobbies,
                "声優": profile.cv,
                "登録日": profile.registration_date,
            }
            for profile in sorted(cls._profiles)
        ]

        with path.open("w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=4, ensure_ascii=False)

        LibsProfilesLogger.info(
            f"{cls.__name__}.save: {len(cls._profiles)}件のアイドルのプロフィール情報データベースを保存しました。"
        )


if __name__ == "__main__":
    print(__file__)
