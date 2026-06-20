import unittest

from math import ceil
from deredata.libs.simulate.appeal import appeal

from deredata.libs.database.idols import Idols
from deredata.libs.database.episodes import Episodes
from deredata.libs.database.buffs import Buffs
from deredata.libs.database.skills import Skills
from deredata.libs.database.musics import Musics
from deredata.libs.database.potentials import Potentials

EPISODE: list = ["［ＳＳレア＋::ドミナント・デュエット（ステップ＆メイク）::ドミナント・ハーモニー］キュート＋"]
EPISODES: list = [
    "［ＳＳレア＋::シンデレラブレス::シンデレラマジック］パッション＋",
    "［ＳＳレア＋::ドミナント・デュエット（ステップ＆メイク）::ドミナント・ハーモニー］キュート＋",
    "［ＳＳレア＋::シンデレラウィッシュ::リフレイン］パッション＋",
    "［Ｓレア＋::パッションステップ::COMBOボーナス］パッション＋",
    "［ＳＳレア＋::パッションステップ::コーディネイト］パッション＋",
    "［ＳＳレア＋::レゾナンス・ステップ::ダンスモチーフ］パッション＋",
]


class TestAppeal(unittest.TestCase):
    def setUp(self) -> None:
        Idols.load("tests/database/idols.json")
        Episodes.load("tests/database/episodes.json")
        Buffs.load("tests/database/buffs.json")
        Skills.load("tests/database/skills.json")
        Potentials.load("tests/database/potentials.json")
        Musics.load("tests/database/music/*.json")

        self.episodes: Episodes = Episodes()
        self.musics: Musics = Musics()

    def test_member(self) -> None:
        # "［ＳＳレア＋::ドミナント・デュエット（ステップ＆メイク）::ドミナント・ハーモニー］キュート＋"
        # 基礎値：vocal=68, dance=7705, visual=7897, life=44, 中確率(0.35)*(1+(10-1)/18), わずかな間(3秒)*(1+(10-1/18))
        # ポテンシャル補正：life=6(+10), vocal=6(+270), dance=6(+270), visula=7(+320), skill=10(+0.2), 0
        # 楽曲タイプ一致：0.3, 0.3, 0.3, 0.0, 0.3, 0.0
        # ルーム効果：0.1, 0.1, 0.1, 0.0, 0.0, 0.0
        # センター効果：0.0, 1.5, 1.6, 0.0, 0.0, 0.0
        # センター効果：0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        self.assertEqual(
            appeal(
                position=0,
                episodes=[self.episodes.get(episode) for episode in EPISODE],
                music=self.musics.get("tests/database/music/sample_DEBUT_PASSION_L5.json"),
            ),
            (
                [
                    ceil((68 + 270) * (1 + 0.1 + 0.3)),
                    ceil((7705.0 + 270.0) * (1.0 + 0.1 + 0.3 + 1.5)),
                    ceil((7897 + 320) * (1 + 0.1 + 0.3 + 1.6)),
                    (44 + 10),
                    (0.35 * (1 + (10 - 1) / 18) + 0.2) * (1 + 0.3),
                    (3.0 * (1 + (10 - 1) / 18)),
                ],
                False,
            ),
        )

    def test_unit_member(self) -> None:
        self.assertEqual(
            appeal(
                position=1,
                episodes=[self.episodes.get(episode) for episode in EPISODES],
                music=self.musics.get("tests/database/music/sample_DEBUT_PASSION_L5.json"),
            ),
            (
                [
                    ceil((68 + 270) * (1 + 0.1 + 0.3)),
                    ceil((7705.0 + 270.0) * (1.0 + 0.1 + 0.3 + 1.5)),
                    ceil((7897 + 320) * (1 + 0.1 + 0.3 + 1.6)),
                    (44 + 10),
                    (0.35 * (1 + (10 - 1) / 18) + 0.2) * (1 + 0.3),
                    (3.0 * (1 + (10 - 1) / 18)),
                ],
                True,
            ),
        )

    def test_support(self) -> None:
        self.assertEqual(
            appeal(
                position=0,
                episodes=[self.episodes.get(episode) for episode in EPISODE],
                music=self.musics.get("tests/database/music/sample_DEBUT_PASSION_L5.json"),
                support=True,
            ),
            (
                [
                    ceil(0.5 * (68 + 270) * (1 + 0.3)),
                    ceil(0.5 * (7705.0 + 270.0) * (1.0 + 0.3)),
                    ceil(0.5 * (7897 + 320) * (1 + 0.3)),
                ],
                False,
            ),
        )


if __name__ == "__main__":
    unittest.main()
