import unittest

from pathlib import Path

from deredata.libs.database.enumerations import IdolType
from deredata.libs.database.idols import Idol, Idols
from deredata.libs.database.profiles import Profile, Profiles
from deredata.libs.database.convert.idols_from_textdata import convert


class TestIdolsConvert(unittest.TestCase):
    def setUp(self) -> None:
        convert(
            idols_txtfilename="tests/textdata/idols.txt",
            idols_fixed_txtfilename="tests/textdata/idols_fixed.txt",
            idols_jsonfilename="tests/database/idols.json",
            profiles_jsonfilename="tests/database/profiles.json",
        )

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/idols.json").is_file())
        self.assertTrue(Path("tests/database/profiles.json").is_file())


class TestIdols(unittest.TestCase):
    def setUp(self) -> None:
        convert(
            idols_txtfilename="tests/textdata/idols.txt",
            idols_fixed_txtfilename="tests/textdata/idols_fixed.txt",
            idols_jsonfilename="tests/database/idols.json",
            profiles_jsonfilename="tests/database/profiles.json",
        )
        Idols.load("tests/database/idols.json")
        Profiles.load("tests/database/profiles.json")
        self.idols: Idols = Idols()
        self.profiles: Profiles = Profiles()

    def test_Idols(self) -> None:
        self.assertEqual(len(self.idols.gets()), 3)
        self.assertEqual(self.idols.get("きゅーと").name, "キュート")

    def test_Profiles(self) -> None:
        self.assertEqual(len(self.profiles.gets()), 3)
        self.assertEqual(self.profiles.get("くーる").zodiac_sign, "獅子座")


if __name__ == "__main__":
    unittest.main()
