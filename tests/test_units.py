import unittest

from deredata.libs.database.units import Positions6, Positions5, Unit, GrandliveUnit, Units, UnitsError


class TestUnits(unittest.TestCase):
    def setUp(self) -> None:
        Units.load("tests/database/units.json")
        self.units: Units = Units()

    def test_Units(self) -> None:

        self.assertIsInstance(self.units, Units)
        self.assertEqual(len(self.units.gets()), 3)

        unit = self.units.get("test_sample0")
        if isinstance(unit, Unit):
            self.assertIsInstance(unit.positions, Positions6)
            self.assertEqual(
                unit.positions.centerposition, "［ＳＳレア＋::シンデレラブレス::シンデレラマジック］クール＋"
            )

        # 存在しないユニット名を指定すると、初期値が得られる。
        unit = self.units.get("test")
        self.assertIsInstance(unit, Unit)
        if isinstance(unit, Unit):
            self.assertIsInstance(unit.positions, Positions6)
            self.assertEqual(unit.positions.centerposition, "センター")

        # 存在しないデータベースファイルを読み込もうとするとエラー
        self.assertRaises(UnitsError, Units.load, "")


if __name__ == "__main__":
    unittest.main()
