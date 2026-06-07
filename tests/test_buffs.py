import unittest
from pathlib import Path

from deredata.libs.database.buffs import Buff, Buffs, BuffsMystyle, BuffsError
from deredata.libs.database.convert.buffs_from_textdata import convert
from deredata.libs.database.convert.buffs_from_textdata_mystyle import convert as convert_mystyle


class TestBuffs(unittest.TestCase):
    def setUp(self) -> None:
        convert(buffs_jsonfilename="tests/database/buffs.json")
        Buffs.load("tests/database/buffs.json")
        self.buffs: Buffs = Buffs()

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/buffs.json").is_file())

    def test_database(self) -> None:
        self.assertEqual(
            len(self.buffs.gets()),
            133,
        )
        self.assertEqual(
            self.buffs.get("キュートアイドルの特技発動確率40%アップ").buff,
            "キュートアビリティ",
        )
        self.assertEqual(
            len(self.buffs.get("キュートアイドルの特技発動確率40%アップ").buffparts),
            1,
        )
        self.assertRaises(
            BuffsError,
            Buffs.load,
            "",
        )


class TestBuffsMystyle(unittest.TestCase):
    def setUp(self) -> None:
        convert_mystyle(buffs_jsonfilename="tests/database/buffs_mystyle.json")
        BuffsMystyle.load("tests/database/buffs_mystyle.json")
        self.buffs: BuffsMystyle = BuffsMystyle()

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/buffs_mystyle.json").is_file())

    def test_database(self) -> None:
        self.assertEqual(
            len(self.buffs.gets()),
            74,
        )
        self.assertEqual(
            self.buffs.get("3タイプ全てのアイドル編成時、全員のダンスアピール値80%アップ").buff,
            "トリコロール・ステップ★2",
        )
        self.assertEqual(
            len(self.buffs.get("3タイプ全てのアイドル編成時、全員のダンスアピール値80%アップ").buffparts),
            1,
        )
        self.assertRaises(
            BuffsError,
            BuffsMystyle.load,
            "",
        )


if __name__ == "__main__":
    unittest.main()
