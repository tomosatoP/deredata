import unittest
from pathlib import Path

from deredata.libs.database.musiclevels import MusicLevel, MusicLevels, MusiclevelsError
from deredata.libs.database.convert.musiclevels_from_textdata import convert


class TestPotentials(unittest.TestCase):
    def setUp(self) -> None:
        convert(musiclevels_jsonfilename="tests/database/musiclevels.json")
        MusicLevels.load("tests/database/musiclevels.json")
        self.musiclevels: MusicLevels = MusicLevels()

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/musiclevels.json").is_file())

    def test_database(self) -> None:
        self.assertEqual(
            self.musiclevels.rate(31),
            2.3,
        )
        self.assertRaises(
            MusiclevelsError,
            MusicLevels.load,
            "",
        )


if __name__ == "__main__":
    unittest.main()
