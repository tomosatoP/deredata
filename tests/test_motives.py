import unittest
from pathlib import Path

from deredata.libs.database.motives import Motif, Motives, MotifError
from deredata.libs.database.convert.motives_from_textdata import convert


class TestMotives(unittest.TestCase):
    def setUp(self) -> None:
        convert(motives_jsonfilename="tests/database/motif.json")
        Motives.load("tests/database/motif.json")
        self.motives: Motives = Motives()

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/motif.json").is_file())

    def test_database(self) -> None:
        self.assertEqual(
            self.motives.value(50000),
            0.26,
        )
        self.assertEqual(
            self.motives.value(50000, True),
            0.32,
        )
        self.assertRaises(
            MotifError,
            Motives.load,
            "",
        )


if __name__ == "__main__":
    unittest.main()
