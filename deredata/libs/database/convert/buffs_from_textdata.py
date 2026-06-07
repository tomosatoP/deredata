"""
テキストデータから、センター効果データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv

from deredata.libs.database.enumerations import IdolType, MusicType, UnitType
from deredata.libs.database.configurations import textdata_folder
from deredata.libs.database.buffs import Buffs, Buff, BuffTriggerType, BuffPart, AppealType, BuffPartTriggerType

buffdatas: Buffs = Buffs()
parts: set[BuffPart] = set()

BUFFDATA: str = textdata_folder() + "buffs.txt"
BUFFPARTDATA: str = textdata_folder() + "buffparts.txt"


def convert(
    buffs_txtfilename: str = BUFFDATA,
    buffparts_txtfilename: str = BUFFPARTDATA,
    buffs_jsonfilename: str | None = None,
) -> None:

    with open(buffparts_txtfilename, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            part = BuffPart(
                name=data["センター効果パーツ"],
                trigger=BuffPartTriggerType(data["適用要件"]),
                music=MusicType(data["適用楽曲"]),
                member=IdolType(data["適用メンバー"]),
                appeal=AppealType(data["適用効果"]),
                value=float(data["効果量"]),
            )
            parts.add(part)

    with open(buffs_txtfilename, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            if data["パーツ番号"] == "1":
                buff = Buff(
                    name=data["センター効果説明"],
                    buff=data["センター効果"],
                    category=data["センター効果分類"],
                    categoryname=data["センター効果分類説明"],
                    trigger=BuffTriggerType(data["発動要件"]),
                    formation=UnitType(data["編成要件"]),
                    music=MusicType(data["楽曲要件"]),
                )
                buffdatas.add(buff)

            buff = list(filter(lambda b: b.name == data["センター効果説明"], buffdatas.gets()))[0]
            part = list(filter(lambda p: p.name == data["センター効果パーツ"], parts))[0]
            new_buff = Buff(
                name=buff.name,
                buff=buff.buff,
                category=buff.category,
                categoryname=buff.categoryname,
                trigger=buff.trigger,
                formation=buff.formation,
                music=buff.music,
                buffparts=buff.buffparts | {part},
            )
            buffdatas.update(after=new_buff, before=buff)

    Buffs.save(buffs_jsonfilename) if buffs_jsonfilename else Buffs.save()


if __name__ == "__main__":
    print(__file__)
    convert()
