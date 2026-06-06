import unittest
from pathlib import Path

from deredata.libs.database.episodes import Episode, Episodes, EpisodesError
from deredata.libs.database.flavors import Flavor, Flavors, FlavorsError
from deredata.libs.database.convert.episodes_from_textdata import convert


class TestEpisodesConvert(unittest.TestCase):
    def setUp(self) -> None:
        convert(
            episodes_txtfilename="tests/textdata/episodes.txt",
            episode_fixed_txtfilename="tests/textdata/episodes_fixed.txt",
            episodes_jsonfilename="tests/database/episodes.json",
            flavors_jsonfilename="tests/database/flavors.json",
        )

    def test_convert(self) -> None:
        self.assertTrue(Path("tests/database/idols.json").is_file())
        self.assertTrue(Path("tests/database/profiles.json").is_file())


class TestEpisodes(unittest.TestCase):
    def setUp(self) -> None:
        convert(
            episodes_txtfilename="tests/textdata/episodes.txt",
            episode_fixed_txtfilename="tests/textdata/episodes_fixed.txt",
            episodes_jsonfilename="tests/database/episodes.json",
            flavors_jsonfilename="tests/database/flavors.json",
        )
        Episodes.load("tests/database/episodes.json")
        Flavors.load("tests/database/flavors.json")
        self.episodes: Episodes = Episodes()
        self.flavors: Flavors = Flavors()

    def test_Idols(self) -> None:
        self.assertEqual(len(self.episodes.gets()), 432)
        self.assertEqual(
            self.episodes.get("［ＳＳレア＋::レゾナンス・メイク::ビジュアルモチーフ］パッション＋").buff_class,
            "レゾナンス・メイク",
        )
        self.assertEqual(
            self.episodes.get("［ＳＳレア＋::レゾナンス・メイク::ビジュアルモチーフ］パッション＋").skill_class,
            "ビジュアルモチーフ",
        )

    def test_Profiles(self) -> None:
        self.assertEqual(len(self.flavors.gets()), 432)
        self.assertEqual(
            self.flavors.get("［ＳＳレア＋::レゾナンス・メイク::ビジュアルモチーフ］パッション＋").registration_date,
            "2020年2月29日",
        )


if __name__ == "__main__":
    unittest.main()
