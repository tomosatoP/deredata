"""
テキストデータから、アイドル＆プロフィールデータベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.enumerations import IdolType
from deredata.libs.database.idols import Idol, Idols
from deredata.libs.database.profiles import Profile, Profiles

idoldatas = Idols()
profiledatas = Profiles()

load_idoldatas = Idols()
load_profiledatas = Profiles()

IDOLDATA: str = textdata_folder() + "idols.txt"

if __name__ == "__main__":
    with open(IDOLDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            idol = Idol(
                ruby=data["ふりがな"],
                name=data["名前"],
                type=IdolType(data["アイドルタイプ"]),
                life=int(data["ライフ"]),
                vocal=int(data["ボーカル"]),
                dance=int(data["ダンス"]),
                visual=int(data["ビジュアル"]),
                skill=int(data["特技"]),
            )
            profile = Profile(
                ruby=data["ふりがな"],
                age=data["年齢"],
                birthday=data["誕生日"].strip("'"),
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
                registration_date=data["登録日"].strip("'"),
            )

            idoldatas.add(idol)
            profiledatas.add(profile)

    idoldatas.save()
    profiledatas.save()

    load_idoldatas.load()
    load_profiledatas.load()

    print(load_idoldatas.get(ruby="しまむらうづき"))
    print(load_profiledatas.get(ruby="しまむらうづき"))
