import unittest

import numpy as np
from math import ceil
from deredata.libs.simulate.appeal import appeal

from deredata.libs.database.idols import Idols
from deredata.libs.database.episodes import Episodes
from deredata.libs.database.buffs import Buffs
from deredata.libs.database.skills import Skills
from deredata.libs.database.potentials import Potentials


class TestAppeal(unittest.TestCase):
    def setUp(self) -> None:
        Idols.load("tests/database/idols.json")
        Episodes.load("tests/database/episodes.json")
        Buffs.load("tests/database/buffs.json")
        Skills.load("tests/database/skills.json")
        Potentials.load("tests/database/potentials.json")
        self.episodes: Episodes = Episodes()

    def test_appeal(self) -> None:
        # "［ＳＳレア＋::ドミナント・デュエット（ステップ＆メイク）::ドミナント・ハーモニー］キュート＋"
        # "パッション楽曲でキュートアイドルにタイプボーナスが発生しダンスアピール値150％アップ、
        #  パッションアイドルのビジュアルアピール値160%アップ"
        # 基礎値：vocal=68, dance=7705, visual=7897, life=44, 中確率(0.35)*(1+(10-1)/18), わずかな間(3秒)*(1+(10-1/18))
        # ポテンシャル補正：life=6(+10), vocal=6(+270), dance=6(+270), visula=7(+320), skill=10(+0.2)
        # 楽曲タイプ一致： 0.3, 0.3, 0.3, 0.0, 0.3, 0.0
        # ルーム効果: 0.1, 0.1, 0.1, 0.0, 0.0, 0.0
        # センター効果：
        self.assertEqual(
            appeal(
                position=0,
                episodes=[
                    self.episodes.get(
                        "［ＳＳレア＋::ドミナント・デュエット（ステップ＆メイク）::ドミナント・ハーモニー］キュート＋"
                    )
                ],
            ),
            [
                ceil((68 + 270) * (1 + 0.1 + 0.3)),
                ceil((7705.0 + 270.0) * (1.0 + 0.1 + 0.3)),
                ceil((7897 + 320) * (1 + 0.1 + 0.3)),
                (44 + 10),
                (0.35 * (1 + (10 - 1) / 18) + 0.2) * (1 + 0.3),
                (3.0 * (1 + (10 - 1) / 18)),
            ],
        )


if __name__ == "__main__":
    unittest.main()
