import unittest
from pathlib import Path

from deredata.libs.database.lifesparkles import Lifesparkle, Lifesparkles, LifesparkleError
from deredata.libs.database.convert.lifesparkles_from_textdata import convert


class TestLifesparkles(unittest.TestCase):
    def setUp(self) -> None:
        convert(lifesparkle_jsonfilename="tests/database/lifesparkle.json")
        Lifesparkles.load("tests/database/lifesparkle.json")
        self.lifesparkles: Lifesparkles = Lifesparkles()

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/lifesparkle.json").is_file())

    def test_database(self) -> None:
        self.assertEqual(
            self.lifesparkles.value(500),
            0.21,
        )
        self.assertEqual(
            self.lifesparkles.value(500, "SR"),
            0.18,
        )
        self.assertRaises(
            LifesparkleError,
            Lifesparkles.load,
            "",
        )


if __name__ == "__main__":
    unittest.main()
