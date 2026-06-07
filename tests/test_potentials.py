import unittest
from pathlib import Path

from deredata.libs.database.potentials import Appeal, Ability, Life, Potentials, PotentialsError
from deredata.libs.database.convert.potentials_from_textdata import convert
from deredata.libs.database.enumerations import RareClass


class TestPotentials(unittest.TestCase):
    def setUp(self) -> None:
        convert(potentials_jsonfilename="tests/database/potentials.json")
        Potentials.load("tests/database/potentials.json")
        self.potentials: Potentials = Potentials()

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/potentials.json").is_file())

    def test_database(self) -> None:
        self.assertEqual(
            self.potentials.value("ボーカル", RareClass.USRPLUS, 10),
            400,
        )
        self.assertEqual(
            self.potentials.value("特技発動率", RareClass.USRPLUS, 10),
            0.25,
        )
        self.assertEqual(
            self.potentials.value("ライフ", RareClass.USRPLUS, 10),
            24,
        )
        self.assertRaises(
            PotentialsError,
            Potentials.load,
            "",
        )


if __name__ == "__main__":
    unittest.main()
