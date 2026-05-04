"""
テキストデータから、アイドル＆プロフィールデータベース（JSONデータ）への変換を扱うモジュール。
"""

import csv
import tomllib

from deredata.libs.database import enums
from deredata.libs.database import idols
from deredata.libs.database import profiles

idoldatas = idols.Idols()
profiledatas = profiles.Profiles()

load_idoldatas = idols.Idols()
load_profiledatas = profiles.Profiles()

if __name__ == "__main__":
    with open("config/config.toml", "rb") as f:
        config = tomllib.load(f)
        TEXTDATAFOLDER: str = config["textdata_folder"]
        IDOLDATA: str = TEXTDATAFOLDER + "idols.txt"

    with open(IDOLDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            idol = idols.Idol(
                ruby=data["ふりがな"],
                name=data["名前"],
                type=enums.IdolType(data["アイドルタイプ"]),
                life=int(data["ライフ"]),
                vocal=int(data["ボーカル"]),
                dance=int(data["ダンス"]),
                visual=int(data["ビジュアル"]),
                skill=int(data["特技"]),
            )
            profile = profiles.Profile(
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
