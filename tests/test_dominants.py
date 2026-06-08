import unittest
from pathlib import Path

from deredata.libs.database.dominants import Dominant, Dominants, DominantError
from deredata.libs.database.convert.dominants_from_textdata import convert


class TestDominants(unittest.TestCase):
    def setUp(self) -> None:
        convert(dominant_jsonfilename="tests/database/dominant.json")
        Dominants.load("tests/database/dominant.json")
        self.dominants: Dominants = Dominants()

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/dominant.json").is_file())

    def test_database(self) -> None:
        self.assertEqual(
            self.dominants.value(3, 0),
            0.3,
        )
        self.assertEqual(
            self.dominants.value(3, 1),
            0.35,
        )
        self.assertEqual(
            self.dominants.value(3, 0, False),
            0.7,
        )
        self.assertEqual(
            self.dominants.value(3, 1, False),
            0.75,
        )
        self.assertRaises(
            DominantError,
            Dominants.load,
            "",
        )


if __name__ == "__main__":
    unittest.main()
