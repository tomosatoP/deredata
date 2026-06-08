"""
テキストデータから、アイドル＆プロフィールデータベース（JSONデータ）への変換を扱うモジュール。

テキストデータを固定（idols_fixed.txt）と更新用（idols.txt）に分割。
更新用（idols.txt）が無い場合、パラメーターを ZERO で埋め、作成。
"""

import csv
from pathlib import Path

from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.enumerations import IdolType
from deredata.libs.database.idols import Idol, Idols
from deredata.libs.database.profiles import Profile, Profiles

idoldatas: Idols = Idols()
profiledatas: Profiles = Profiles()

IDOLFIXEDDATA: str = textdata_folder() + "idols_fixed.txt"
IDOLDATA: str = textdata_folder() + "idols.txt"


def convert(
    idols_txtfilename: str = IDOLDATA,
    idols_fixed_txtfilename: str = IDOLFIXEDDATA,
    idols_jsonfilename: str | None = None,
    profiles_jsonfilename: str | None = None,
) -> None:
    """
    アイドル情報のテキストデータをデータベース（JSON形式）に変換する。

    :param str idols_txtfilename:
        アイドルのポテンシャルデータのファイル名。
        無い場合は、ポテンシャル値を ZERO にセットする。
        未指定の場合は、既定のファイル名。
    :param str idols_fixed_txtfilename:
        アイドルのポテンシャルデータ以外の固定データのファイル名。
        未指定の場合は、既定のファイル名。
    :param str idols_jsonfilename:
        アイドルの基礎情報データベースのファイル名。
        未指定の場合は、既定のファイル名。
    :param str profiles_jsonfilename:
        アイドルのプロフィール情報データベースのファイル名。
        未指定の場合は、既定のファイル名。
    """

    with open(idols_fixed_txtfilename, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            idol = Idol(
                ruby=data["ふりがな"],
                name=data["名前"],
                type=IdolType(data["アイドルタイプ"]),
                life=0,
                vocal=0,
                dance=0,
                visual=0,
                skill=0,
                over=0,
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

    if Path(idols_txtfilename).is_file():
        with open(idols_txtfilename, "r", encoding="utf-8-sig") as f:
            datas = csv.DictReader(f)

            for data in datas:
                idol_fixed = idoldatas.get(data["ふりがな"])
                idol = Idol(
                    ruby=data["ふりがな"],
                    name=idol_fixed.name,
                    type=idol_fixed.type,
                    life=int(data["ライフ"]),
                    vocal=int(data["ボーカル"]),
                    dance=int(data["ダンス"]),
                    visual=int(data["ビジュアル"]),
                    skill=int(data["特技"]),
                    over=int(data["余り"]),
                )
                idoldatas.update(after=idol, before=idol_fixed)
    else:
        with open(idols_txtfilename, "w", encoding="utf-8-sig", newline="") as f:
            fieldnames: list[str] = [
                "ふりがな",
                "ライフ",
                "ボーカル",
                "ダンス",
                "ビジュアル",
                "特技",
                "余り",
                "合計",
            ]
            writer = csv.DictWriter(f=f, fieldnames=fieldnames)

            writer.writeheader()
            for idol in sorted(idoldatas.gets()):
                writer.writerow(
                    {
                        "ふりがな": idol.ruby,
                        "ライフ": str(idol.life),
                        "ボーカル": str(idol.vocal),
                        "ダンス": str(idol.dance),
                        "ビジュアル": str(idol.visual),
                        "特技": str(idol.skill),
                        "余り": str(idol.over),
                        "合計": str(idol.life + idol.vocal + idol.dance + idol.visual + idol.skill + idol.over),
                    }
                )

    Idols.save(idols_jsonfilename) if idols_jsonfilename else Idols.save()
    Profiles.save(profiles_jsonfilename) if profiles_jsonfilename else Profiles.save()


if __name__ == "__main__":
    print(__file__)
    convert()
