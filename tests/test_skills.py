import unittest
from pathlib import Path

from deredata.libs.database.skills import Skill, Skills, SkillsMystyle, SkillsError
from deredata.libs.database.convert.skills_from_textdata import convert
from deredata.libs.database.convert.skills_from_textdata_mystyle import convert as convert_mystyle


class TestSkills(unittest.TestCase):
    def setUp(self) -> None:
        convert(skills_jsonfilename="tests/database/skills.json")
        Skills.load("tests/database/skills.json")
        self.skills: Skills = Skills()

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/skills.json").is_file())

    def test_database(self) -> None:
        self.assertEqual(
            len(self.skills.gets()),
            260,
        )
        self.assertEqual(
            self.skills.get("10秒毎、中確率で少しの間、NICEでもCOMBOが継続する").skill,
            "COMBOサポート",
        )
        self.assertEqual(
            len(self.skills.get("10秒毎、中確率で少しの間、NICEでもCOMBOが継続する").skillparts),
            1,
        )
        self.assertRaises(
            SkillsError,
            Skills.load,
            "",
        )


class TestSkillsMystyle(unittest.TestCase):
    def setUp(self) -> None:
        convert_mystyle(skills_jsonfilename="tests/database/skills_mystyle.json")
        SkillsMystyle.load("tests/database/skills_mystyle.json")
        self.skills: SkillsMystyle = SkillsMystyle()

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/skills_mystyle.json").is_file())

    def test_database(self) -> None:
        self.assertEqual(
            len(self.skills.gets()),
            107,
        )
        self.assertEqual(
            self.skills.get("10秒毎、高確率でわずかな間、PERFECTでライフ3回復").skill,
            "ライフ回復★2 / 10秒高確率",
        )
        self.assertEqual(
            len(self.skills.get("10秒毎、高確率でわずかな間、PERFECTでライフ3回復").skillparts),
            1,
        )
        self.assertRaises(
            SkillsError,
            SkillsMystyle.load,
            "",
        )


if __name__ == "__main__":
    unittest.main()
