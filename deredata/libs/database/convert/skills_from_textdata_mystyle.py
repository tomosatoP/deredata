"""
テキストデータから、マイスタイルアイドルの特技データベース（JSONデータ）への変換を扱うモジュール。
"""

import csv
import tomllib

from deredata.libs.database.enums import IdolType, MusicType, UnitType
from deredata.libs.database.skills import (
    Skill,
    SkillsMystyle,
    SkillPart,
    SkillTriggerType,
    ProbabilityType,
    DurationType,
    BuffType,
    IconType,
    PerfectionType,
    EffectType,
)

skilldatas = SkillsMystyle()
load_skilldatas = SkillsMystyle()

parts: set[SkillPart] = set()


def isfloat(data: str) -> bool:
    try:
        float(data)
    except ValueError:
        return False
    else:
        return True


if __name__ == "__main__":
    with open("config/config.toml", "rb") as ff:
        config = tomllib.load(ff)
        TEXTDATAFOLDER: str = config["textdata_folder"]
        SKILLDATA: str = TEXTDATAFOLDER + "mystyle_skills.txt"
        SKILLPARTDATA: str = TEXTDATAFOLDER + "mystyle_skillparts.txt"

    with open(SKILLPARTDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            part = SkillPart(
                name=data["特技パーツ"],
                bufftype=BuffType(data["特技パーツ効果分類"]),
                member=IdolType(data["適用メンバー"]),
                icon=IconType(data["適用アイコン"]),
                perfection=PerfectionType(data["適用判定"]),
                effect=EffectType(data["特技パーツ効果"]),
                value=float(data["効果量"]) if isfloat(data["効果量"]) else data["効果量"],
            )
            parts.add(part)

    with open(SKILLDATA, "r", encoding="utf-8-sig") as f:
        datas = csv.DictReader(f)

        for data in datas:
            if data["パーツ番号"] == "1":
                buff = Skill(
                    name=data["特技説明"],
                    skill=data["特技"],
                    category=data["特技分類"],
                    trigger=SkillTriggerType(data["発動要件"]),
                    music=MusicType(data["楽曲要件"]),
                    formation=UnitType(data["編成要件"]),
                    interval=int(data["発動間隔"]),
                    probability=ProbabilityType(data["発動確率"]),
                    duration=DurationType(data["継続期間"]),
                )
                skilldatas.add(buff)

            skill = list(filter(lambda s: s.name == data["特技説明"], skilldatas.gets()))[0]
            part = list(filter(lambda p: p.name == data["特技パーツ"], parts))[0]
            new_skill = Skill(
                name=skill.name,
                skill=skill.skill,
                category=skill.category,
                trigger=skill.trigger,
                music=skill.music,
                formation=skill.formation,
                interval=skill.interval,
                probability=skill.probability,
                duration=skill.duration,
                skillparts=skill.skillparts | {part},
            )
            skilldatas.update(after=new_skill, before=skill)

    skilldatas.save()

    load_skilldatas.load()

    print(
        load_skilldatas.get(
            "9秒毎、中確率でライフを15消費し、しばらくの間PERFECT/GREATのスコア18%アップ、NICE/BADでもCOMBO継続"
        )
    )
