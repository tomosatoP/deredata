import unittest
from pathlib import Path

from deredata.libs.database.comborates import Comborate, ComboRates, ComboratesError
from deredata.libs.database.convert.comborates_from_textdata import convert


class TestComboretes(unittest.TestCase):
    def setUp(self) -> None:
        convert(comborate_jsonfilename="tests/database/comborate.json")
        ComboRates.load("tests/database/comborate.json")
        self.comoborates: ComboRates = ComboRates()

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/comborate.json").is_file())

    def test_database(self) -> None:
        self.assertEqual(
            self.comoborates.rate(0.88),
            1.7,
        )
        self.assertRaises(
            ComboratesError,
            ComboRates.load,
            "",
        )


if __name__ == "__main__":
    unittest.main()
